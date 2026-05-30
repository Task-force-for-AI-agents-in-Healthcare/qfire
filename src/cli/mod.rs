//! The QFIRE command-line interface.
//!
//! Follows cargo/kubectl conventions: subcommands, aligned columnar human output
//! by default, a `--json` flag on every command for machine-readable output, and
//! a `--quiet` flag for CI. Exit codes are meaningful so QFIRE can gate
//! pipelines: `0` = allowed, `2` = blocked, `1` = error.

mod rules_cmd;

use crate::app::App;
use crate::ir::LlmRequest;
use crate::output;
use crate::verdict::Verdict;
use clap::{Args, Parser, Subcommand};
use std::io::Read;
use std::path::PathBuf;

/// Exit codes used throughout the CLI.
pub mod exit {
    pub const ALLOW: i32 = 0;
    pub const ERROR: i32 = 1;
    pub const BLOCK: i32 = 2;
}

#[derive(Parser)]
#[command(
    name = "qfire",
    version,
    about = "QFIRE — a prompt firewall for LLM applications",
    long_about = "QFIRE evaluates inbound prompts against declarative firewall rules and \
                  forwards to a downstream provider only on ALLOW. Surfaces: a proxy port, \
                  this CLI, structured output, and benchmark report artifacts."
)]
pub struct Cli {
    /// Path to a config file (default: ./qfire.toml or ~/.config/qfire/config.toml).
    #[arg(long, global = true)]
    pub config: Option<PathBuf>,

    /// Emit machine-readable JSON instead of human output.
    #[arg(long, global = true)]
    pub json: bool,

    /// Suppress non-essential output (for CI).
    #[arg(long, global = true)]
    pub quiet: bool,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Run the proxy daemon with wire-compatible provider endpoints.
    Serve(ServeArgs),
    /// Evaluate a prompt against a chain and print the verdict (no downstream call).
    Check(CheckArgs),
    /// Evaluate and, if allowed, execute the downstream call.
    Run(RunArgs),
    /// Manage the rule library (list, lint, test, explain).
    #[command(subcommand)]
    Rules(rules_cmd::RulesCommand),
    /// Replay an attack corpus through chains and emit research metrics.
    Bench(BenchArgs),
    /// Import or mutate attack corpora (garak / PyRIT adapters).
    #[command(subcommand)]
    Attack(AttackCommand),
    /// Summarize an audit log.
    Report(ReportArgs),
}

#[derive(Args)]
pub struct PromptInput {
    /// The prompt text. Use `-` to read from stdin, or omit and use --file.
    pub prompt: Option<String>,
    /// Read the prompt from a file.
    #[arg(long)]
    pub file: Option<PathBuf>,
    /// An optional system prompt.
    #[arg(long)]
    pub system: Option<String>,
    /// The downstream model name (defaults to the profile's model).
    #[arg(long)]
    pub model: Option<String>,
}

impl PromptInput {
    fn into_request(self, default_model: &str) -> crate::Result<LlmRequest> {
        let text = if let Some(path) = &self.file {
            std::fs::read_to_string(path)?
        } else {
            match self.prompt.as_deref() {
                Some("-") | None => {
                    let mut s = String::new();
                    std::io::stdin().read_to_string(&mut s)?;
                    s
                }
                Some(p) => p.to_string(),
            }
        };
        let model = self.model.unwrap_or_else(|| default_model.to_string());
        let mut req = LlmRequest::user(model, text.trim_end());
        req.system = self.system;
        Ok(req)
    }
}

#[derive(Args)]
pub struct CheckArgs {
    #[command(flatten)]
    pub input: PromptInput,
    /// The chain (or rule) to evaluate against.
    #[arg(long, short = 'c', default_value = "default")]
    pub chain: String,
}

#[derive(Args)]
pub struct RunArgs {
    #[command(flatten)]
    pub input: PromptInput,
    #[arg(long, short = 'c', default_value = "default")]
    pub chain: String,
    /// Override the downstream provider profile.
    #[arg(long)]
    pub provider: Option<String>,
}

#[derive(Args)]
pub struct ServeArgs {
    /// Address to bind, e.g. 127.0.0.1:8787.
    #[arg(long, default_value = "127.0.0.1:8787")]
    pub addr: String,
    /// The default chain applied when a request selects none.
    #[arg(long, default_value = "default")]
    pub chain: String,
    /// Redact block reasons in the refusal envelope returned to clients.
    #[arg(long)]
    pub redact: bool,
}

#[derive(Args)]
pub struct BenchArgs {
    /// One or more chains to benchmark.
    #[arg(long = "chain", short = 'c', required = true)]
    pub chains: Vec<String>,
    /// Directory of attack prompts (one per line in .txt, or .jsonl with `prompt`).
    #[arg(long, default_value = "corpora/attacks")]
    pub attacks: PathBuf,
    /// Directory of benign in-scope prompts.
    #[arg(long, default_value = "corpora/benign")]
    pub benign: PathBuf,
    /// Output directory for CSV/JSON/Markdown artifacts.
    #[arg(long, default_value = "bench-out")]
    pub out: PathBuf,
    /// Random seed for deterministic runs.
    #[arg(long, default_value_t = 42)]
    pub seed: u64,
    /// Also run attack-in-prompt (camouflaged) mutations of benign prompts.
    #[arg(long)]
    pub attack_in_prompt: bool,
    /// Limit prompts per corpus (0 = all).
    #[arg(long, default_value_t = 0)]
    pub limit: usize,
}

#[derive(Subcommand)]
pub enum AttackCommand {
    /// Import a corpus from garak/PyRIT output or a labeled file into corpora/.
    Import(AttackImportArgs),
    /// Mutate benign prompts into attack-in-prompt variants (PyRIT-style).
    Mutate(AttackMutateArgs),
}

#[derive(Args)]
pub struct AttackImportArgs {
    /// Source file (garak .jsonl report, PyRIT export, or a .txt of prompts).
    pub source: PathBuf,
    /// Source format.
    #[arg(long, default_value = "auto")]
    pub format: String,
    /// Destination file under corpora/.
    #[arg(long)]
    pub out: PathBuf,
}

#[derive(Args)]
pub struct AttackMutateArgs {
    /// Benign prompts file to camouflage attacks inside.
    pub benign: PathBuf,
    /// Output file of mutated attack-in-prompt cases.
    #[arg(long)]
    pub out: PathBuf,
    #[arg(long, default_value_t = 42)]
    pub seed: u64,
}

#[derive(Args)]
pub struct ReportArgs {
    /// Path to the audit log (JSONL).
    #[arg(default_value = "audit.jsonl")]
    pub path: PathBuf,
}

/// Parse args and dispatch, returning a process exit code.
pub async fn run() -> i32 {
    let cli = Cli::parse();
    match dispatch(cli).await {
        Ok(code) => code,
        Err(e) => {
            eprintln!("error: {e}");
            exit::ERROR
        }
    }
}

async fn dispatch(cli: Cli) -> crate::Result<i32> {
    let color = !cli.quiet && output::use_color();
    match cli.command {
        Command::Check(args) => {
            let app = App::load(cli.config.as_deref())?;
            let model = default_model(&app);
            let req = args.input.into_request(&model)?;
            let decision = app.check(&args.chain, &req).await?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(&decision)?);
            } else if cli.quiet {
                println!("{}", decision.terminal.label());
            } else {
                print!("{}", output::render_decision(&decision, color));
            }
            Ok(exit_for(decision.terminal))
        }
        Command::Run(args) => {
            let app = App::load(cli.config.as_deref())?;
            let model = default_model(&app);
            let req = args.input.into_request(&model)?;
            let (decision, response) = app.run(&args.chain, &req, args.provider.as_deref()).await?;
            if cli.json {
                let val = serde_json::json!({ "decision": decision, "response": response });
                println!("{}", serde_json::to_string_pretty(&val)?);
            } else {
                if !cli.quiet {
                    print!("{}", output::render_decision(&decision, color));
                    println!("{}", "─".repeat(60));
                }
                match response {
                    Some(r) => {
                        println!("{}", r.content);
                        if !cli.quiet {
                            eprintln!(
                                "[{} tokens, ${:.6}]",
                                r.usage.total_tokens(),
                                r.usage.cost_usd
                            );
                        }
                    }
                    None => {
                        if !cli.quiet {
                            eprintln!("(blocked — downstream not contacted)");
                        }
                    }
                }
            }
            Ok(exit_for(decision.terminal))
        }
        Command::Rules(cmd) => {
            rules_cmd::run(cmd, cli.config.as_deref(), cli.json, cli.quiet).await
        }
        Command::Serve(args) => {
            let app = App::load(cli.config.as_deref())?;
            crate::proxy::serve(app, &args.addr, &args.chain, args.redact).await?;
            Ok(exit::ALLOW)
        }
        Command::Bench(args) => {
            let app = App::load(cli.config.as_deref())?;
            crate::bench::run_bench(&app, &args, cli.json).await?;
            Ok(exit::ALLOW)
        }
        Command::Attack(cmd) => crate::bench::run_attack(cmd, cli.json).await,
        Command::Report(args) => report(&args, cli.json),
    }
}

fn exit_for(v: Verdict) -> i32 {
    match v {
        Verdict::Allow => exit::ALLOW,
        Verdict::Block => exit::BLOCK,
        _ => exit::ERROR,
    }
}

/// The default model name from the default provider profile.
pub fn default_model(app: &App) -> String {
    app.config
        .providers
        .first()
        .and_then(|p| p.model.clone())
        .unwrap_or_else(|| "llama3.2".to_string())
}

fn report(args: &ReportArgs, json: bool) -> crate::Result<i32> {
    let records = crate::audit::AuditLog::read_all(&args.path)?;
    if json {
        println!("{}", serde_json::to_string_pretty(&records)?);
        return Ok(exit::ALLOW);
    }
    let total = records.len();
    let allowed = records.iter().filter(|r| r.terminal == Verdict::Allow).count();
    let blocked = records.iter().filter(|r| r.terminal == Verdict::Block).count();
    let avg_wall: f64 = if total > 0 {
        records.iter().map(|r| r.wall_clock_ms).sum::<f64>() / total as f64
    } else {
        0.0
    };
    let cost: f64 = records.iter().filter_map(|r| r.usage.as_ref()).map(|u| u.cost_usd).sum();
    println!("audit: {}", args.path.display());
    println!("  records:   {total}");
    println!("  allowed:   {allowed}");
    println!("  blocked:   {blocked}");
    println!("  avg wall:  {avg_wall:.1}ms");
    println!("  total cost: ${cost:.6}");
    Ok(exit::ALLOW)
}
