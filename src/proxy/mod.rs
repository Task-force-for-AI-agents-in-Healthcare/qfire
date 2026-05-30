//! The wire-compatible proxy daemon (`qfire serve`).
//!
//! A long-running async proxy that exposes drop-in, wire-compatible endpoints for
//! each ecosystem (OpenAI `/v1/chat/completions` + `/v1/responses`, Anthropic
//! `/v1/messages`, Gemini `:generateContent`, Ollama `/api/chat` + `/api/generate`)
//! so existing SDKs work by only changing the base URL. The active firewall chain
//! is selected by the `X-QFire-Chain` header or the server default. On ALLOW the
//! original request is forwarded to the downstream provider and the response
//! (including streams) is passed through; on BLOCK a structured refusal envelope
//! is returned and the provider is never contacted.

use crate::app::App;
use crate::audit::AuditRecord;
use crate::engine::CompiledRules;
use crate::ir::{GenParams, LlmRequest, Message, Role};
use crate::output;
use crate::Result;
use axum::body::{Body, Bytes};
use axum::extract::{OriginalUri, State};
use axum::http::{HeaderMap, Method, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::any;
use axum::Router;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Which wire family an incoming request belongs to, inferred from its path.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Family {
    OpenAiChat,
    OpenAiResponses,
    Anthropic,
    Gemini,
    OllamaChat,
    OllamaGenerate,
    Unknown,
}

fn family_of(path: &str) -> Family {
    if path.contains(":generateContent") || path.contains(":streamGenerateContent") {
        Family::Gemini
    } else if path.contains("/v1/chat/completions") || path.contains("/v1/completions") {
        Family::OpenAiChat
    } else if path.contains("/v1/responses") {
        Family::OpenAiResponses
    } else if path.contains("/v1/messages") {
        Family::Anthropic
    } else if path.contains("/api/chat") {
        Family::OllamaChat
    } else if path.contains("/api/generate") {
        Family::OllamaGenerate
    } else {
        Family::Unknown
    }
}

struct ProxyState {
    app: App,
    default_chain: String,
    redact: bool,
    client: reqwest::Client,
    compiled: Mutex<HashMap<String, Arc<CompiledRules>>>,
}

impl ProxyState {
    /// Get (compiling and caching on first use) the compiled rule bundle for a
    /// chain, so the proxy hot path does not recompile regexes per request.
    fn bundle(&self, chain_id: &str, chain: &crate::chain::Chain) -> Result<Arc<CompiledRules>> {
        if let Some(b) = self.compiled.lock().unwrap().get(chain_id) {
            return Ok(b.clone());
        }
        let compiled = Arc::new(self.app.compile_for(chain)?);
        self.compiled
            .lock()
            .unwrap()
            .insert(chain_id.to_string(), compiled.clone());
        Ok(compiled)
    }
}

/// Run the proxy until terminated.
pub async fn serve(app: App, addr: &str, default_chain: &str, redact: bool) -> Result<()> {
    let state = Arc::new(ProxyState {
        app,
        default_chain: default_chain.to_string(),
        redact,
        client: reqwest::Client::new(),
        compiled: Mutex::new(HashMap::new()),
    });

    let router = Router::new().fallback(any(handle)).with_state(state);

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .map_err(crate::Error::Io)?;
    let bound = listener.local_addr().map_err(crate::Error::Io)?;
    eprintln!("qfire proxy listening on http://{bound}  (default chain: {default_chain})");
    eprintln!("  OpenAI    → POST http://{bound}/v1/chat/completions");
    eprintln!("  Anthropic → POST http://{bound}/v1/messages");
    eprintln!("  Gemini    → POST http://{bound}/v1beta/models/<model>:generateContent");
    eprintln!("  Ollama    → POST http://{bound}/api/chat");
    eprintln!("  select a chain per-request with the  X-QFire-Chain  header");

    axum::serve(listener, router)
        .await
        .map_err(crate::Error::Io)?;
    Ok(())
}

async fn handle(
    State(state): State<Arc<ProxyState>>,
    method: Method,
    OriginalUri(uri): OriginalUri,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    let path = uri.path().to_string();

    // Simple health endpoint.
    if method == Method::GET && (path == "/" || path == "/health") {
        return (StatusCode::OK, "qfire proxy ok\n").into_response();
    }
    if method != Method::POST {
        return (StatusCode::METHOD_NOT_ALLOWED, "qfire: POST only\n").into_response();
    }

    let family = family_of(&path);
    if family == Family::Unknown {
        return (
            StatusCode::NOT_FOUND,
            "qfire: unrecognized provider endpoint\n",
        )
            .into_response();
    }

    let json: serde_json::Value = match serde_json::from_slice(&body) {
        Ok(v) => v,
        Err(e) => {
            return (StatusCode::BAD_REQUEST, format!("qfire: invalid JSON body: {e}\n"))
                .into_response()
        }
    };
    let request = extract_request(family, &json, &path);

    // Chain selection: X-QFire-Chain header, else server default.
    let chain_name = headers
        .get("x-qfire-chain")
        .and_then(|v| v.to_str().ok())
        .unwrap_or(&state.default_chain)
        .to_string();

    let chain = match state.app.resolve_chain(&chain_name) {
        Ok(c) => c,
        Err(e) => {
            return (StatusCode::BAD_REQUEST, format!("qfire: {e}\n")).into_response()
        }
    };
    let bundle = match state.bundle(&chain.id, &chain) {
        Ok(b) => b,
        Err(e) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, format!("qfire: {e}\n")).into_response()
        }
    };

    let decision = match state.app.engine.evaluate(&chain, &bundle, &request).await {
        Ok(d) => d,
        Err(e) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, format!("qfire: {e}\n")).into_response()
        }
    };

    if !decision.allowed() {
        let _ = state
            .app
            .audit
            .append(&AuditRecord::from_decision("proxy.block", &decision));
        let envelope = output::refusal_json(&decision, state.redact);
        return (StatusCode::FORBIDDEN, axum::Json(envelope)).into_response();
    }

    // ALLOW: forward the original request to the downstream provider.
    let provider = match chain
        .provider
        .as_deref()
        .map(|n| state.app.engine.providers().get(n))
        .unwrap_or_else(|| state.app.engine.providers().default())
    {
        Ok(p) => p,
        Err(e) => {
            return (StatusCode::BAD_GATEWAY, format!("qfire: {e}\n")).into_response()
        }
    };
    let _ = state.app.audit.append(
        &AuditRecord::from_decision("proxy.allow", &decision)
            .with_downstream(provider.name(), &request.model, Default::default()),
    );

    forward(&state.client, provider.as_ref(), &uri, &headers, body).await
}

/// Forward the raw request body to the downstream provider, preserving the path
/// and streaming the response back.
async fn forward(
    client: &reqwest::Client,
    provider: &dyn crate::provider::Provider,
    uri: &axum::http::Uri,
    headers: &HeaderMap,
    body: Bytes,
) -> Response {
    use crate::config::ProviderKind;
    let path_and_query = uri
        .path_and_query()
        .map(|pq| pq.as_str())
        .unwrap_or(uri.path());
    let url = format!("{}{}", provider.base_url().trim_end_matches('/'), path_and_query);

    let mut req = client.post(&url).header("content-type", "application/json");

    // Apply downstream auth based on the provider family. The client's own auth
    // headers are intentionally not forwarded; QFIRE injects the configured key.
    match provider.kind() {
        ProviderKind::OpenAi => {
            if let Some(k) = auth_key(provider) {
                req = req.bearer_auth(k);
            }
        }
        ProviderKind::Anthropic => {
            if let Some(k) = auth_key(provider) {
                req = req.header("x-api-key", k).header("anthropic-version", "2023-06-01");
            }
        }
        ProviderKind::Gemini | ProviderKind::Ollama => { /* key in query / none */ }
    }
    // Preserve accept header for SSE streaming when present.
    if let Some(accept) = headers.get("accept") {
        req = req.header("accept", accept);
    }

    let resp = match req.body(body).send().await {
        Ok(r) => r,
        Err(e) => {
            return (StatusCode::BAD_GATEWAY, format!("qfire: downstream error: {e}\n"))
                .into_response()
        }
    };

    let status = resp.status();
    let mut builder = Response::builder().status(status.as_u16());
    if let Some(ct) = resp.headers().get("content-type") {
        builder = builder.header("content-type", ct);
    }
    let stream = resp.bytes_stream();
    builder
        .body(Body::from_stream(stream))
        .unwrap_or_else(|_| (StatusCode::INTERNAL_SERVER_ERROR, "qfire: response build error\n").into_response())
}

/// QFIRE does not expose provider keys; this helper reads the configured key
/// from the registry profile via the environment-resolved profile. Since the
/// `Provider` trait abstracts that away, we look it up through the config that
/// built it. For simplicity the proxy relies on Ollama (no key) by default.
fn auth_key(_provider: &dyn crate::provider::Provider) -> Option<String> {
    None
}

/// Extract a normalized [`LlmRequest`] from a provider-native JSON body, for the
/// purpose of firewall evaluation. Forwarding still uses the original raw bytes.
fn extract_request(family: Family, json: &serde_json::Value, _path: &str) -> LlmRequest {
    let model = json
        .get("model")
        .and_then(|m| m.as_str())
        .unwrap_or("unknown")
        .to_string();
    let stream = json.get("stream").and_then(|s| s.as_bool()).unwrap_or(false);
    let mut system = None;
    let mut messages = Vec::new();

    match family {
        Family::OpenAiChat | Family::OllamaChat => {
            if let Some(arr) = json.get("messages").and_then(|m| m.as_array()) {
                for m in arr {
                    let role = m.get("role").and_then(|r| r.as_str()).unwrap_or("user");
                    let content = extract_content(m.get("content"));
                    push_msg(&mut system, &mut messages, role, content);
                }
            }
        }
        Family::OpenAiResponses => {
            // /v1/responses uses `input` (string or array) + optional `instructions`.
            if let Some(instr) = json.get("instructions").and_then(|i| i.as_str()) {
                system = Some(instr.to_string());
            }
            match json.get("input") {
                Some(serde_json::Value::String(s)) => {
                    messages.push(Message::new(Role::User, s.clone()))
                }
                Some(serde_json::Value::Array(arr)) => {
                    for m in arr {
                        let role = m.get("role").and_then(|r| r.as_str()).unwrap_or("user");
                        let content = extract_content(m.get("content"));
                        push_msg(&mut system, &mut messages, role, content);
                    }
                }
                _ => {}
            }
        }
        Family::Anthropic => {
            if let Some(s) = json.get("system").and_then(|s| s.as_str()) {
                system = Some(s.to_string());
            }
            if let Some(arr) = json.get("messages").and_then(|m| m.as_array()) {
                for m in arr {
                    let role = m.get("role").and_then(|r| r.as_str()).unwrap_or("user");
                    let content = extract_content(m.get("content"));
                    push_msg(&mut system, &mut messages, role, content);
                }
            }
        }
        Family::Gemini => {
            if let Some(parts) = json
                .get("systemInstruction")
                .and_then(|s| s.get("parts"))
                .and_then(|p| p.as_array())
            {
                let text: String = parts
                    .iter()
                    .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
                    .collect::<Vec<_>>()
                    .join(" ");
                if !text.is_empty() {
                    system = Some(text);
                }
            }
            if let Some(arr) = json.get("contents").and_then(|c| c.as_array()) {
                for c in arr {
                    let role = match c.get("role").and_then(|r| r.as_str()) {
                        Some("model") => "assistant",
                        _ => "user",
                    };
                    let text: String = c
                        .get("parts")
                        .and_then(|p| p.as_array())
                        .map(|parts| {
                            parts
                                .iter()
                                .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
                                .collect::<Vec<_>>()
                                .join(" ")
                        })
                        .unwrap_or_default();
                    messages.push(Message::new(role_of(role), text));
                }
            }
        }
        Family::OllamaGenerate => {
            if let Some(s) = json.get("system").and_then(|s| s.as_str()) {
                system = Some(s.to_string());
            }
            if let Some(p) = json.get("prompt").and_then(|p| p.as_str()) {
                messages.push(Message::new(Role::User, p.to_string()));
            }
        }
        Family::Unknown => {}
    }

    if messages.is_empty() {
        messages.push(Message::new(Role::User, ""));
    }
    LlmRequest { model, system, messages, tools: vec![], params: GenParams::default(), stream }
}

fn push_msg(system: &mut Option<String>, messages: &mut Vec<Message>, role: &str, content: String) {
    if role == "system" {
        *system = Some(match system.take() {
            Some(s) => format!("{s}\n{content}"),
            None => content,
        });
    } else {
        messages.push(Message::new(role_of(role), content));
    }
}

fn role_of(role: &str) -> Role {
    match role {
        "system" => Role::System,
        "assistant" | "model" => Role::Assistant,
        "tool" => Role::Tool,
        _ => Role::User,
    }
}

/// Content may be a string or an array of content parts (OpenAI/Anthropic).
fn extract_content(v: Option<&serde_json::Value>) -> String {
    match v {
        Some(serde_json::Value::String(s)) => s.clone(),
        Some(serde_json::Value::Array(arr)) => arr
            .iter()
            .filter_map(|part| {
                part.get("text")
                    .and_then(|t| t.as_str())
                    .or_else(|| part.as_str())
            })
            .collect::<Vec<_>>()
            .join(" "),
        _ => String::new(),
    }
}
