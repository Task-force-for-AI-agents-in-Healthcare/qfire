//! QFIRE — a prompt firewall for LLM applications.
//!
//! QFIRE evaluates inbound prompts against declarative *firewall rules* (each a
//! typed detector pipeline), collapses per-rule verdicts into a single terminal
//! ALLOW/BLOCK decision with a fully explainable trace, and — when used as a
//! proxy — forwards the original request to a downstream provider only on ALLOW.
//!
//! The crate is organized into focused modules with clear boundaries:
//!
//! - [`ir`] — provider-independent internal representation of requests/responses
//! - [`verdict`] — verdict types shared across detectors, rules and chains
//! - [`detector`] — the [`detector::Detector`] trait and built-in detector nodes
//! - [`rule`] — the declarative YAML rule model
//! - [`chain`] — rule chaining and collapse (ordered + expression modes)
//! - [`engine`] — the parallel evaluation engine, verdict cache and fail policy
//! - [`provider`] — the unified provider client over OpenAI/Anthropic/Gemini/Ollama
//! - [`audit`] — the immutable, attributable audit log
//! - [`config`] — provider profiles and runtime configuration
//! - [`proxy`] — the wire-compatible proxy daemon
//! - [`bench`] — the benchmark harness and corpus adapters
//! - [`output`] — human-readable and `--json` rendering

pub mod app;
pub mod audit;
pub mod bench;
pub mod chain;
pub mod cli;
pub mod config;
pub mod detector;
pub mod engine;
pub mod error;
pub mod ir;
pub mod output;
pub mod provider;
pub mod proxy;
pub mod rule;
pub mod ruleset;
pub mod verdict;

pub use error::{Error, Result};
pub use verdict::{NodeVerdict, Verdict};

/// The QFIRE version string, embedded in audit records and run manifests.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
