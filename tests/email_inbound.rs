//! The `email_inbound` chain: corpus gates, offline guarantees, and the CLI
//! contract a subprocess caller relies on (`check --json --chain email_inbound -`,
//! exit 0 = allow, 2 = block, rule id in `deciding_rule`).

use qfire::app::App;
use qfire::config::{Config, ProviderKind, ProviderProfile};
use qfire::detector::NodeConfig;
use qfire::engine::Engine;
use qfire::ir::LlmRequest;
use qfire::verdict::Verdict;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::time::Instant;

const CHAIN: &str = "email_inbound";

fn manifest() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
}

fn config() -> Config {
    Config {
        rules_dir: manifest().join("rules").to_string_lossy().into_owned(),
        chains_dir: manifest().join("chains").to_string_lossy().into_owned(),
        audit_path: "".into(),
        ..Config::default()
    }
}

fn app() -> App {
    App::from_config(config()).unwrap()
}

/// An app whose only provider (Ollama) refuses connections.
fn offline_app() -> App {
    let mut cfg = config();
    cfg.providers = vec![ProviderProfile {
        name: "ollama".into(),
        kind: ProviderKind::Ollama,
        base_url: Some("http://127.0.0.1:1".into()),
        api_key: None,
        model: Some("llama3.2".into()),
    }];
    App::from_config(cfg).unwrap()
}

/// `(id, prompt)` pairs from every `.jsonl` file under `dir`.
fn corpus(dir: &str) -> Vec<(String, String)> {
    let dir = manifest().join(dir);
    let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("{}: {e}", dir.display()))
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("jsonl"))
        .collect();
    files.sort();
    let mut out = Vec::new();
    for f in files {
        for line in std::fs::read_to_string(&f).unwrap().lines() {
            if line.trim().is_empty() {
                continue;
            }
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            out.push((
                v["id"].as_str().unwrap().to_string(),
                v["prompt"].as_str().unwrap().to_string(),
            ));
        }
    }
    assert!(!out.is_empty(), "empty corpus: {}", dir.display());
    out
}

fn benign() -> Vec<(String, String)> {
    corpus("corpora/email/benign")
}

fn attacks() -> Vec<(String, String)> {
    corpus("corpora/email/attacks")
}

async fn verdicts(app: &App, chain: &str, items: &[(String, String)]) -> Vec<(String, Verdict)> {
    let mut out = Vec::new();
    for (id, p) in items {
        let d = app.check(chain, &LlmRequest::user("m", p)).await.unwrap();
        out.push((id.clone(), d.terminal));
    }
    out
}

#[tokio::test]
async fn benign_corpus_all_allowed() {
    let app = app();
    let mut bad = Vec::new();
    for (id, p) in benign() {
        let d = app.check(CHAIN, &LlmRequest::user("m", &p)).await.unwrap();
        if d.terminal != Verdict::Allow {
            bad.push(format!("{id}: {:?} by {:?}", d.terminal, d.deciding_rule));
        }
    }
    assert!(bad.is_empty(), "benign not allowed:\n{}", bad.join("\n"));
}

#[tokio::test]
async fn attack_corpus_all_blocked() {
    let app = app();
    let mut bad = Vec::new();
    for (id, p) in attacks() {
        let d = app.check(CHAIN, &LlmRequest::user("m", &p)).await.unwrap();
        if d.terminal != Verdict::Block {
            bad.push(format!("{id}: {:?}", d.terminal));
        }
    }
    assert!(bad.is_empty(), "attacks not blocked:\n{}", bad.join("\n"));
}

#[test]
fn chain_has_no_network_nodes() {
    let app = app();
    let chain = app.resolve_chain(CHAIN).unwrap();
    let compiled = app.compile_for(&chain).unwrap();
    assert!(!compiled.is_empty());
    for (id, cr) in &compiled {
        for node in &cr.rule.pipeline {
            let network = matches!(node, NodeConfig::Judge { .. })
                || matches!(
                    node,
                    NodeConfig::Similarity {
                        embed_model: Some(_),
                        ..
                    }
                );
            assert!(!network, "rule '{id}' has a network node: {node:?}");
        }
    }
}

#[tokio::test]
async fn offline_verdicts_unchanged() {
    let online = app();
    let offline = offline_app();
    for items in [benign(), attacks()] {
        let a = verdicts(&online, CHAIN, &items).await;
        let b = verdicts(&offline, CHAIN, &items).await;
        assert_eq!(a, b);
    }
}

/// Run the binary exactly as the subprocess caller does, from an unrelated cwd.
fn run_cli(stdin: &str) -> (Output, tempfile::TempDir) {
    let t = tempfile::tempdir().unwrap();
    let toml = t.path().join("qfire.toml");
    std::fs::write(
        &toml,
        format!(
            "rules_dir = {:?}\nchains_dir = {:?}\naudit_path = \"\"\n",
            manifest().join("rules").to_string_lossy(),
            manifest().join("chains").to_string_lossy(),
        ),
    )
    .unwrap();
    let mut child = Command::new(env!("CARGO_BIN_EXE_qfire"))
        .current_dir(t.path())
        .env("QFIRE_CONFIG", &toml)
        .args(["check", "--json", "--chain", CHAIN, "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin.as_bytes())
        .unwrap();
    (child.wait_with_output().unwrap(), t)
}

#[test]
fn cli_contract_block() {
    let (_, prompt) = attacks().remove(0);
    let (out, _t) = run_cli(&prompt);
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2), "stderr: {stderr}");
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["terminal"], "block");
    let rule = v["deciding_rule"].as_str().unwrap_or("");
    assert!(!rule.is_empty(), "json: {v}");
    let app = app();
    let refs = app
        .resolve_chain(CHAIN)
        .unwrap()
        .referenced_rules()
        .unwrap();
    assert!(refs.iter().any(|r| r == rule), "'{rule}' not in chain");
}

#[test]
fn cli_contract_allow() {
    let (_, prompt) = benign().remove(0);
    let (out, _t) = run_cli(&prompt);
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(0), "stderr: {stderr}");
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["terminal"], "allow");
}

#[tokio::test]
async fn huge_benign_input_is_fast_and_allowed() {
    let app = app();
    let (_, base) = benign().remove(0);
    let body = base.split_once("\n\n").map(|(_, b)| b).unwrap_or(&base);
    let mut p = String::from("Subject: Your monthly statement\n\n");
    while p.len() + body.len() + 2 <= 200_000 {
        p.push_str(body);
        p.push_str("\n\n");
    }
    // Time the evaluation itself (rules compiled once, outside the timer), with
    // the verdict cache off; take the best of 3 so a busy host does not flake.
    let chain = app.resolve_chain(CHAIN).unwrap();
    let compiled = app.compile_for(&chain).unwrap();
    let engine = Engine::new(app.engine.providers().clone()).with_cache(false);
    let req = LlmRequest::user("m", &p);
    let mut elapsed = std::time::Duration::MAX;
    let mut d = None;
    for _ in 0..3 {
        let start = Instant::now();
        let r = engine.evaluate(&chain, &compiled, &req).await.unwrap();
        elapsed = elapsed.min(start.elapsed());
        d = Some(r);
    }
    let d = d.unwrap();
    assert_eq!(d.terminal, Verdict::Allow, "by {:?}", d.deciding_rule);
    let limit = if cfg!(debug_assertions) { 3.0 } else { 1.0 };
    assert!(
        elapsed.as_secs_f64() < limit,
        "{} bytes took {elapsed:?}",
        p.len()
    );
}

#[tokio::test]
async fn empty_body_allows() {
    let d = app()
        .check(CHAIN, &LlmRequest::user("m", "Subject: \n\n"))
        .await
        .unwrap();
    assert_eq!(d.terminal, Verdict::Allow);
}

#[tokio::test]
async fn crlf_attack_still_blocks() {
    let (_, p) = attacks()
        .into_iter()
        .find(|(_, p)| p.contains("AI agents: disregard"))
        .expect("corpus has the 'AI agents: disregard' entry");
    let crlf = p.replace('\n', "\r\n");
    let d = app()
        .check(CHAIN, &LlmRequest::user("m", &crlf))
        .await
        .unwrap();
    assert_eq!(d.terminal, Verdict::Block);
}
