//! The benchmark harness (`qfire bench`) and attack-corpus adapters.
//!
//! Replays a corpus of attack prompts and a paired corpus of benign in-scope
//! prompts through one or more chains and computes, per rule and per chain:
//! successful-injection rate, block rate, false-positive/negative rates,
//! precision/recall/F1, AUC (from node scores), latency (p50/p95/p99) and the
//! firewall's token/cost overhead. Runs are deterministic and seeded and fully
//! described by a run manifest, so results are reproducible and citable.

mod corpus;
mod metrics;
mod report;

pub use corpus::{load_prompts, Corpus};
pub use metrics::Metrics;

use crate::app::App;
use crate::cli::{exit, AttackCommand};
use crate::ir::LlmRequest;
use crate::verdict::Verdict;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;
use serde::Serialize;
use std::collections::HashMap;

/// One evaluated sample: a labeled prompt and the chain's response to it.
#[derive(Clone)]
pub struct Sample {
    pub is_attack: bool,
    pub terminal: Verdict,
    /// The chain's block-score: the maximum node injection/block score in the
    /// trace, used for ROC/AUC.
    pub score: f64,
    pub wall_clock_ms: f64,
    pub summed_detector_ms: f64,
    /// Per-rule verdicts from the trace, for per-rule metrics.
    pub rule_verdicts: HashMap<String, Verdict>,
}

/// The full result of a benchmark run for one chain.
#[derive(Serialize)]
pub struct ChainReport {
    pub chain: String,
    pub chain_version: String,
    pub overall: Metrics,
    pub per_rule: Vec<(String, Metrics)>,
    /// Attack-in-prompt (camouflaged) metrics, when that mode was run.
    pub attack_in_prompt: Option<Metrics>,
}

/// The run manifest embedded in every artifact for reproducibility.
#[derive(Serialize, Clone)]
pub struct Manifest {
    pub qfire_version: String,
    pub timestamp: String,
    pub seed: u64,
    pub model: String,
    pub chains: Vec<String>,
    pub attack_count: usize,
    pub benign_count: usize,
    pub attack_in_prompt: bool,
}

/// Run the benchmark across the requested chains and write artifacts.
pub async fn run_bench(app: &App, args: &crate::cli::BenchArgs, json: bool) -> crate::Result<()> {
    let mut attacks = load_prompts(&args.attacks)?;
    let mut benign = load_prompts(&args.benign)?;
    if args.limit > 0 {
        attacks.truncate(args.limit);
        benign.truncate(args.limit);
    }
    if attacks.is_empty() && benign.is_empty() {
        return Err(crate::Error::Config(format!(
            "no prompts found under {} or {}",
            args.attacks.display(),
            args.benign.display()
        )));
    }

    let manifest = Manifest {
        qfire_version: crate::VERSION.to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        seed: args.seed,
        model: crate::cli::default_model(app),
        chains: args.chains.clone(),
        attack_count: attacks.len(),
        benign_count: benign.len(),
        attack_in_prompt: args.attack_in_prompt,
    };

    if !json {
        eprintln!(
            "bench: {} attacks, {} benign, {} chain(s), seed {}",
            attacks.len(),
            benign.len(),
            args.chains.len(),
            args.seed
        );
    }

    // Build a dedicated engine so the verdict cache can be disabled for honest,
    // un-warmed per-chain latency (and so chains don't share cached verdicts).
    let engine = crate::engine::Engine::new(app.engine.providers().clone())
        .with_cache(!args.no_cache);

    let mut reports = Vec::new();
    for chain_name in &args.chains {
        let report = bench_chain(app, &engine, chain_name, &attacks, &benign, args).await?;
        reports.push(report);
    }

    // Write artifacts.
    std::fs::create_dir_all(&args.out)?;
    report::write_json(&args.out, &manifest, &reports)?;
    report::write_csv(&args.out, &reports)?;
    report::write_markdown(&args.out, &manifest, &reports)?;

    if json {
        let val = serde_json::json!({ "manifest": manifest, "reports": reports });
        println!("{}", serde_json::to_string_pretty(&val)?);
    } else {
        print!("{}", report::render_console(&manifest, &reports));
        eprintln!("\nartifacts written to {}/", args.out.display());
    }
    Ok(())
}

async fn bench_chain(
    app: &App,
    engine: &crate::engine::Engine,
    chain_name: &str,
    attacks: &[String],
    benign: &[String],
    args: &crate::cli::BenchArgs,
) -> crate::Result<ChainReport> {
    let chain = app.resolve_chain(chain_name)?;
    let compiled = app.compile_for(&chain)?;
    let referenced = chain.referenced_rules()?;

    let mut samples: Vec<Sample> = Vec::new();
    for (prompts, is_attack) in [(attacks, true), (benign, false)] {
        for p in prompts {
            let req = LlmRequest::user("bench", p);
            let decision = engine.evaluate(&chain, &compiled, &req).await?;
            samples.push(sample_from(&decision, is_attack));
        }
    }

    // Optional per-prompt prediction dump (corpus order: attacks then benign),
    // for paired tests (McNemar) and bootstrap CIs across chains.
    if let Some(dir) = &args.dump {
        std::fs::create_dir_all(dir)?;
        use std::io::Write as _;
        let mut f = std::fs::File::create(dir.join(format!("{}.jsonl", chain.id)))?;
        for s in &samples {
            writeln!(
                f,
                "{}",
                serde_json::json!({
                    "is_attack": s.is_attack,
                    "blocked": s.terminal == Verdict::Block,
                    "score": s.score
                })
            )?;
        }
    }

    let overall = Metrics::from_samples(&samples, |s| s.terminal == Verdict::Block, |s| s.score);
    let per_rule = referenced
        .iter()
        .map(|rid| {
            let rid2 = rid.clone();
            let m = Metrics::from_samples(
                &samples,
                move |s| s.rule_verdicts.get(&rid2) == Some(&Verdict::Block),
                |s| s.score,
            );
            (rid.clone(), m)
        })
        .collect();

    // Attack-in-prompt: camouflage payloads inside benign prompts.
    let attack_in_prompt = if args.attack_in_prompt {
        let mut rng = ChaCha8Rng::seed_from_u64(args.seed);
        let mutated = corpus::attack_in_prompt(benign, &mut rng);
        let mut aip_samples = Vec::new();
        for p in &mutated {
            let req = LlmRequest::user("bench", p);
            let decision = engine.evaluate(&chain, &compiled, &req).await?;
            aip_samples.push(sample_from(&decision, true));
        }
        Some(Metrics::from_samples(
            &aip_samples,
            |s| s.terminal == Verdict::Block,
            |s| s.score,
        ))
    } else {
        None
    };

    Ok(ChainReport {
        chain: chain.id.clone(),
        chain_version: chain.version.clone(),
        overall,
        per_rule,
        attack_in_prompt,
    })
}

fn sample_from(decision: &crate::engine::Decision, is_attack: bool) -> Sample {
    // Coherent chain block-score for ROC/AUC: every node contributes a value in
    // [0,1] -- the calibrated injection probability for scoring detectors
    // (deberta/judge/similarity), or the block-confidence for lexical blockers
    // (regex/aho/entropy), which contribute only when they actually BLOCK. This
    // avoids mixing raw entropy bits (a different scale) into the ranking score,
    // which previously inverted the AUC for multi-detector chains.
    let score = decision
        .trace
        .rules
        .iter()
        .flat_map(|r| r.nodes.iter())
        .map(|n| match n.kind.as_str() {
            "deberta" | "judge" | "similarity" => n.score.unwrap_or(n.confidence),
            _ => {
                if n.verdict == Verdict::Block {
                    n.confidence
                } else {
                    0.0
                }
            }
        })
        .fold(0.0_f64, f64::max);
    let rule_verdicts = decision
        .trace
        .rules
        .iter()
        .map(|r| (r.rule_id.clone(), r.verdict))
        .collect();
    Sample {
        is_attack,
        terminal: decision.terminal,
        score,
        wall_clock_ms: decision.trace.wall_clock_ms,
        summed_detector_ms: decision.trace.summed_detector_ms,
        rule_verdicts,
    }
}

/// `qfire attack` subcommands.
pub async fn run_attack(cmd: AttackCommand, json: bool) -> crate::Result<i32> {
    match cmd {
        AttackCommand::Import(args) => {
            let prompts = corpus::import(&args.source, &args.format)?;
            corpus::write_jsonl(&args.out, &prompts, &args.source.display().to_string())?;
            if json {
                println!(
                    "{}",
                    serde_json::json!({ "imported": prompts.len(), "out": args.out.display().to_string() })
                );
            } else {
                println!("imported {} prompts → {}", prompts.len(), args.out.display());
            }
            Ok(exit::ALLOW)
        }
        AttackCommand::Mutate(args) => {
            let benign = load_prompts(&args.benign)?;
            let mut rng = ChaCha8Rng::seed_from_u64(args.seed);
            let mutated = corpus::attack_in_prompt(&benign, &mut rng);
            corpus::write_jsonl(&args.out, &mutated, "attack-in-prompt")?;
            if json {
                println!(
                    "{}",
                    serde_json::json!({ "mutated": mutated.len(), "out": args.out.display().to_string() })
                );
            } else {
                println!("wrote {} attack-in-prompt cases → {}", mutated.len(), args.out.display());
            }
            Ok(exit::ALLOW)
        }
    }
}
