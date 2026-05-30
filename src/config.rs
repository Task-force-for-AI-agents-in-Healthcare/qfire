//! Provider profiles and runtime configuration.
//!
//! Configuration is plain TOML, loaded from (in order) an explicit `--config`
//! path, `./qfire.toml`, or `~/.config/qfire/config.toml`. If no file is found,
//! a built-in default profile pointing at local Ollama is used so QFIRE works
//! offline with zero setup.

use crate::{Error, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

/// A provider family.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderKind {
    OpenAi,
    Anthropic,
    Gemini,
    Ollama,
}

impl ProviderKind {
    pub fn as_str(self) -> &'static str {
        match self {
            ProviderKind::OpenAi => "openai",
            ProviderKind::Anthropic => "anthropic",
            ProviderKind::Gemini => "gemini",
            ProviderKind::Ollama => "ollama",
        }
    }

    /// The conventional default base URL for this provider family.
    pub fn default_base_url(self) -> &'static str {
        match self {
            ProviderKind::OpenAi => "https://api.openai.com",
            ProviderKind::Anthropic => "https://api.anthropic.com",
            ProviderKind::Gemini => "https://generativelanguage.googleapis.com",
            ProviderKind::Ollama => "http://localhost:11434",
        }
    }
}

/// A named provider profile: credentials + base URL for one downstream.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderProfile {
    pub name: String,
    pub kind: ProviderKind,
    /// Base URL override; defaults to the family default.
    #[serde(default)]
    pub base_url: Option<String>,
    /// API key, or the name of an env var to read it from (`env:OPENAI_API_KEY`).
    #[serde(default)]
    pub api_key: Option<String>,
    /// A default model for this profile (used when a request omits one).
    #[serde(default)]
    pub model: Option<String>,
}

impl ProviderProfile {
    /// The effective base URL.
    pub fn effective_base_url(&self) -> String {
        self.base_url
            .clone()
            .unwrap_or_else(|| self.kind.default_base_url().to_string())
    }

    /// Resolve the API key, expanding an `env:VAR` reference.
    pub fn resolve_key(&self) -> Option<String> {
        match &self.api_key {
            None => None,
            Some(k) => {
                if let Some(var) = k.strip_prefix("env:") {
                    std::env::var(var).ok()
                } else {
                    Some(k.clone())
                }
            }
        }
    }
}

/// Top-level QFIRE configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Provider profiles. The first listed is the default.
    #[serde(default)]
    pub providers: Vec<ProviderProfile>,
    /// Directory holding the YAML rule library.
    #[serde(default = "default_rules_dir")]
    pub rules_dir: String,
    /// Directory holding chain definitions.
    #[serde(default = "default_chains_dir")]
    pub chains_dir: String,
    /// Path to the append-only audit log.
    #[serde(default = "default_audit_path")]
    pub audit_path: String,
}

fn default_rules_dir() -> String {
    "rules".into()
}
fn default_chains_dir() -> String {
    "chains".into()
}
fn default_audit_path() -> String {
    "audit.jsonl".into()
}

impl Default for Config {
    fn default() -> Self {
        Config {
            providers: vec![ProviderProfile {
                name: "ollama".into(),
                kind: ProviderKind::Ollama,
                base_url: None,
                api_key: None,
                model: Some("llama3.2".into()),
            }],
            rules_dir: default_rules_dir(),
            chains_dir: default_chains_dir(),
            audit_path: default_audit_path(),
        }
    }
}

impl Config {
    /// Load configuration, searching standard locations when `explicit` is None.
    /// Falls back to a built-in Ollama-only default if nothing is found.
    pub fn load(explicit: Option<&Path>) -> Result<Config> {
        let candidates: Vec<std::path::PathBuf> = match explicit {
            Some(p) => vec![p.to_path_buf()],
            None => {
                let mut v = vec![std::path::PathBuf::from("qfire.toml")];
                if let Some(home) = dirs::config_dir() {
                    v.push(home.join("qfire").join("config.toml"));
                }
                v
            }
        };
        for path in candidates {
            if path.exists() {
                let text = std::fs::read_to_string(&path)?;
                let cfg: Config = toml::from_str(&text)
                    .map_err(|e| Error::Config(format!("{}: {e}", path.display())))?;
                return Ok(cfg);
            }
        }
        if let Some(p) = explicit {
            return Err(Error::Config(format!("config not found: {}", p.display())));
        }
        Ok(Config::default())
    }

    /// Look up a profile by name.
    pub fn profile(&self, name: &str) -> Option<&ProviderProfile> {
        self.providers.iter().find(|p| p.name == name)
    }
}
