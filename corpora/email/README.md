# Email corpus (`email_inbound` chain)

Regression corpus for the `email_inbound` chain: inbound service mail that an
AI agent will read, such as the inbox an agent uses to sign up for services.

- `benign/benign.jsonl`: ordinary service mail that must be ALLOWed:
  verification and login codes, magic links, password resets, receipts,
  invoices, plan and security notices, product announcements, newsletters,
  and footers that name a `support@` address. It includes the hard cases:
  imperative sentences with an address ("Please send any questions to ..."),
  passive "we sent the code to ...", an accented name, a Japanese footer and a
  long base64url magic-link token.
- `attacks/attacks.jsonl`: visible-text injections that must be BLOCKed:
  AgentDojo-style `<INFORMATION>` wrappers, InjecAgent-style product reviews,
  attack-in-prompt payloads inside verification mail, ChatML and `[INST]`
  delimiters, role and markdown-header injections, base64 / hex /
  percent-encoded payloads, `curl ... | sh`, and concealment requests.

## Format

One JSON object per line:

```json
{"id": "acme_verification_code", "prompt": "Subject: ...\n\n<visible text>", "source": "synthetic"}
```

`prompt` has the shape a caller sends to `qfire check --chain email_inbound -`:
a `Subject:` line, a blank line, then the message's visible text.

## Provenance and scope

Everything here is synthetic and was written for this corpus. No third-party
dataset text is included; the attack families are modelled on published
benchmarks (AgentDojo, InjecAgent) but rewritten. Senders are fictional (Acme,
Globex, Initech, Northwind, Contoso, Umbrella, Hooli), addresses use
`example.com`, `example.net` or `example.test`, and every code and token is fake.

Not covered: hidden-HTML text, Unicode tag characters, lookalike links and
display-name spoofing. A caller is expected to detect those while it extracts
the visible text, before qfire runs.

The numbers from this corpus (`make bench-email`) are a regression guard for
the rules, not an estimate of production false-positive rate.
