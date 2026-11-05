//! Provider profiles and runtime configuration.
//!
//! Configuration is plain TOML, loaded from (in order) an explicit `--config`
//! path, the `QFIRE_CONFIG` environment variable (if set and non-empty),
//! `./qfire.toml`, or `~/.config/qfire/config.toml`. If no file is found, a
//! built-in default profile pointing at local Ollama is used so QFIRE works
//! offline with zero setup.
//!
//! When the file came from `QFIRE_CONFIG`, a relative `rules_dir`,
//! `chains_dir` or `audit_path` is resolved against that file's directory, so
//! `qfire` can run as a subprocess from any working directory. Every other
//! source (including `--config`) keeps the historical behaviour: relative
//! paths resolve against the current directory. A missing file named by
//! `--config` or `QFIRE_CONFIG` is an error. `audit_path = ""` disables the
//! audit log.

use crate::{Error, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

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
        let env_path = std::env::var_os("QFIRE_CONFIG")
            .filter(|v| !v.is_empty())
            .map(PathBuf::from);
        // An explicit path (flag, then env var) is the only candidate and must exist.
        // Only a path from QFIRE_CONFIG gets config-relative path resolution.
        let from_env = explicit.is_none() && env_path.is_some();
        let named = explicit.map(Path::to_path_buf).or(env_path);
        let candidates: Vec<PathBuf> = match &named {
            Some(p) => vec![p.clone()],
            None => {
                let mut v = vec![PathBuf::from("qfire.toml")];
                if let Some(home) = dirs::config_dir() {
                    v.push(home.join("qfire").join("config.toml"));
                }
                v
            }
        };
        for path in candidates {
            if path.exists() {
                let text = std::fs::read_to_string(&path)?;
                let mut cfg: Config = toml::from_str(&text)
                    .map_err(|e| Error::Config(format!("{}: {e}", path.display())))?;
                if from_env {
                    let base = path.parent().unwrap_or_else(|| Path::new(""));
                    cfg.rules_dir = resolve_relative(base, &cfg.rules_dir);
                    cfg.chains_dir = resolve_relative(base, &cfg.chains_dir);
                    if !cfg.audit_path.is_empty() {
                        cfg.audit_path = resolve_relative(base, &cfg.audit_path);
                    }
                }
                return Ok(cfg);
            }
        }
        if let Some(p) = named {
            return Err(Error::Config(format!("config not found: {}", p.display())));
        }
        Ok(Config::default())
    }

    /// Look up a profile by name.
    pub fn profile(&self, name: &str) -> Option<&ProviderProfile> {
        self.providers.iter().find(|p| p.name == name)
    }
}

/// Join a relative path onto `base`; an absolute (or empty) path is returned as-is.
pub fn resolve_relative(base: &Path, p: &str) -> String {
    let path = Path::new(p);
    if p.is_empty() || path.is_absolute() {
        p.to_string()
    } else {
        base.join(path).to_string_lossy().into_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_relative_keeps_absolute() {
        assert_eq!(resolve_relative(Path::new("/a"), "/x/rules"), "/x/rules");
        assert_eq!(resolve_relative(Path::new("/a"), "rules"), "/a/rules");
    }
}
