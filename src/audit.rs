//! The immutable, attributable audit log.
//!
//! Every proxy decision and every benchmark trial is appended as one JSON line
//! (JSONL): timestamp, prompt hash, chain + rule + detector versions, per-node
//! verdicts, terminal decision, provider, model, tokens, cost and latency. The
//! log is append-only and is the system of record for live monitoring and
//! offline reproducibility.

use crate::engine::Decision;
use crate::ir::Usage;
use crate::verdict::Verdict;
use crate::Result;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

/// One audit record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditRecord {
    pub ts: String,
    pub qfire_version: String,
    pub event: String,
    pub prompt_hash: String,
    pub chain_id: String,
    pub chain_version: String,
    pub terminal: Verdict,
    pub deciding_rule: Option<String>,
    pub deciding_node: Option<String>,
    pub reason: String,
    pub wall_clock_ms: f64,
    pub summed_detector_ms: f64,
    /// Compact per-node summary: rule_id, node kind, version, verdict, confidence.
    pub nodes: Vec<NodeSummary>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<Usage>,
}

/// A compact node line in an audit record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeSummary {
    pub rule: String,
    pub kind: String,
    pub version: String,
    pub verdict: Verdict,
    pub confidence: f64,
    pub latency_ms: f64,
}

impl AuditRecord {
    /// Build an audit record from a decision.
    pub fn from_decision(event: &str, decision: &Decision) -> Self {
        let mut nodes = Vec::new();
        for rt in &decision.trace.rules {
            for n in &rt.nodes {
                nodes.push(NodeSummary {
                    rule: rt.rule_id.clone(),
                    kind: n.kind.clone(),
                    version: n.version.clone(),
                    verdict: n.verdict,
                    confidence: n.confidence,
                    latency_ms: n.latency_ms,
                });
            }
        }
        AuditRecord {
            ts: Utc::now().to_rfc3339(),
            qfire_version: crate::VERSION.to_string(),
            event: event.to_string(),
            prompt_hash: decision.prompt_hash.clone(),
            chain_id: decision.trace.chain_id.clone(),
            chain_version: decision.trace.chain_version.clone(),
            terminal: decision.terminal,
            deciding_rule: decision.deciding_rule.clone(),
            deciding_node: decision.deciding_node.clone(),
            reason: decision.reason.clone(),
            wall_clock_ms: decision.trace.wall_clock_ms,
            summed_detector_ms: decision.trace.summed_detector_ms,
            nodes,
            provider: None,
            model: None,
            usage: None,
        }
    }

    pub fn with_downstream(mut self, provider: &str, model: &str, usage: Usage) -> Self {
        self.provider = Some(provider.to_string());
        self.model = Some(model.to_string());
        self.usage = Some(usage);
        self
    }
}

/// An append-only audit log writer.
pub struct AuditLog {
    path: PathBuf,
    lock: Mutex<()>,
    enabled: bool,
}

impl AuditLog {
    /// Open (or create) an audit log at `path`.
    pub fn open(path: impl AsRef<Path>) -> Self {
        AuditLog {
            path: path.as_ref().to_path_buf(),
            lock: Mutex::new(()),
            enabled: true,
        }
    }

    /// A no-op audit log (used when auditing is disabled, e.g. dry-run explain).
    pub fn disabled() -> Self {
        AuditLog { path: PathBuf::new(), lock: Mutex::new(()), enabled: false }
    }

    /// Append a record as one JSON line. Thread-safe.
    pub fn append(&self, record: &AuditRecord) -> Result<()> {
        if !self.enabled {
            return Ok(());
        }
        let line = serde_json::to_string(record)?;
        let _guard = self.lock.lock().unwrap();
        let mut file = OpenOptions::new().create(true).append(true).open(&self.path)?;
        writeln!(file, "{line}")?;
        Ok(())
    }

    /// Read all records back (for `qfire report` / offline analysis).
    pub fn read_all(path: impl AsRef<Path>) -> Result<Vec<AuditRecord>> {
        let text = std::fs::read_to_string(path)?;
        let mut out = Vec::new();
        for line in text.lines() {
            if line.trim().is_empty() {
                continue;
            }
            if let Ok(rec) = serde_json::from_str::<AuditRecord>(line) {
                out.push(rec);
            }
        }
        Ok(out)
    }
}
