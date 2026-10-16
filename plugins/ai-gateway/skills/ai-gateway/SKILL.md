---
name: ai-gateway
description: >-
  Two primitives of the Nutrient AI Gateway. Chat models (`nutrient-s`/`nutrient-m`/`nutrient-l`
  via `POST /responses` or `POST /chat/completions`) are OpenAI-compatible, for open-ended
  generation. The decision API (`POST /systemone`, TypeSafe-compatible) returns calibrated
  probabilities instead of free text, for routing, flagging, and scoring — `noul` for yes/no,
  `choice` for picking one of several labels, `score` for placing content on an ordered scale.
  Route to the decision API whenever the task is "classify this", "is this true/false", "route
  to a category", "flag for review", "rate the severity/quality", or anything else that would
  otherwise need regex, keyword matching, or asking a chat model to emit structured JSON. Route
  to a chat model for open-ended generation, summarization, or tool-calling. Triggers include AI
  Gateway, nutrient-decision, nutrient-systemone, System One, TypeSafe, calibrated probability,
  noul question, choice question, score question, classify this document/message, route to a
  category, flag for review, confidence threshold.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.0"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Plain HTTPS/JSON — any language, any agent. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Call OpenAI-compatible chat models or the TypeSafe-compatible decision API via Nutrient AI Gateway"
---

# Nutrient AI Gateway

Two primitives, no bundled script — AI Gateway is a plain REST API, so write the call in
whatever language the project already uses. **Chat models** (`nutrient-s`, `nutrient-m`,
`nutrient-l`) answer `POST /responses` or `POST /chat/completions` with OpenAI-compatible
request/response shapes. **Decision models** (`nutrient-decision`, `nutrient-systemone`) answer
`POST /systemone` with a calibrated probability instead of free text.

## Choosing chat vs. decision

| The task is… | Use | Why |
|---|---|---|
| "Is this true/false", "classify this", "route to a category", "flag for review", "rate the severity/quality" | **Decision API** (`/systemone`) | Returns a calibrated probability or confidence, not text to re-parse — replaces regex, keyword matching, or asking a chat model for JSON it might get wrong |
| Open-ended generation, summarization, drafting, tool-calling | **Chat model** (`/responses` or `/chat/completions`) | Free-text output is the point |
| Structured extraction from a document (fields, tables, citations) | Neither — use the sibling `document-extraction-api` skill | AI Gateway decides *about* content; it doesn't parse documents |

The decision API's whole purpose is standing in for fragile code: a `noul` question
replaces a keyword-matching `if`/`else`; a `choice` question replaces a brittle classifier or
lookup table; a `score` question replaces a hand-tuned heuristic scale. If you're about to write
a regex or a long `if`/`elif` chain to decide something about text, consider a decision question
instead.

## Question types (`POST /systemone`)

One request can carry multiple named `questions` evaluated independently against one shared
`state` (any JSON: string, object, or array):

| Type | Returns | Use for |
|---|---|---|
| `noul` | `{noul}` — a probability from 0 to 1 that the answer is "yes" — **not a Boolean** | Yes/no judgments: "Is this about billing?", "Is this amount plausible?" |
| `choice` | `{choice, confidence, probabilities}` — `choice` is a label from `criteria`, `probabilities` maps every label to its probability | Picking one of several categories: support-ticket routing, sentiment buckets |
| `score` | `{score, confidence, legend, probabilities}` — `score` is the **probability-weighted index** (e.g. `1.43` on a 3-level scale), not necessarily an integer; `legend` maps each 0-based index to its `criteria` label; `probabilities` is keyed by index, not label | Placing content on a scale: severity, quality, confidence tier |

Don't treat `score` as an integer level — round or bucket it deliberately (e.g. `Math.round(score)`
then look up `legend[rounded]`) rather than assuming it lands exactly on a level. `confidence` on
`score` is *not* the same metric as `confidence` on `choice`: a `score` neighbor-level probability
costs less confidence than the same probability on a distant level, so the two aren't comparable
across question types.

Label/level limits differ by model: `nutrient-systemone` accepts up to 255 `choice` labels and
2–10 `score` levels; `nutrient-decision` accepts at most 26 `choice` labels and 2–26 `score`
levels (each option must tokenize to a single native label — a request exceeding either model's
limit is rejected with HTTP 400, `upstream_rejected_request`).

```bash
curl --fail-with-body https://api.nutrient.io/ai/v1/systemone \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nutrient-decision",
    "state": "I was charged twice for my subscription this month.",
    "questions": {
      "billing": { "type": "noul", "instructions": "Is this message about billing?" },
      "category": {
        "type": "choice",
        "instructions": "Which support category applies?",
        "criteria": { "billing": "A billing or payment issue", "bug": "A product defect", "question": "A how-to question" }
      }
    }
  }'
```

Read `answers.billing.noul` as a probability, not a Boolean — choose a decision threshold using
your own evaluation data, and route uncertain results for review rather than hard-coding 0.5.

## Two decision models — pick one, know the difference

- **`nutrient-decision`** (recommended) — Nutrient's own model, run on Nutrient infrastructure.
  Accepts images embedded anywhere in `state`, at any nesting depth, as
  `{"type": "image", "source": "data:<mime>;base64,<bytes>"}`; surrounding text and every
  embedded image are evaluated together.
- **`nutrient-systemone`** — a third-party-provider model. **Text-only** — embedding an image in
  a `nutrient-systemone` request is rejected the same way any other unsupported question shape
  is.

Don't assume feature parity between the two just because they share a request format — check
`GET /models` for what's actually available to the calling key before relying on a capability
(image input, specific label counts) that only one of them has.

## Chat models (`POST /responses`, `POST /chat/completions`)

`nutrient-s` / `nutrient-m` / `nutrient-l` are OpenAI-compatible: send the normal Responses or
Chat Completions request shape, get the normal response shape back. Prefer `/responses` for new
integrations — it supports the model's advertised reasoning levels together with function tools.
Live keys accept inline or URL-based images (`/chat/completions` specifically: up to 10 images
per request, inline data URLs up to 7 MiB, remote URLs up to 4096 bytes); test keys are
text-only.

```bash
curl --fail-with-body https://api.nutrient.io/ai/v1/responses \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nutrient-m",
    "input": "Rewrite this incident note in two plain sentences a non-technical stakeholder can understand: Production database is returning 500s for all write requests since 14:02 UTC; read traffic is unaffected. Root cause under investigation."
  }'
```

## Setup

- Create an API key in the [AI Gateway dashboard](https://dashboard.nutrient.io/ai-gateway/api_keys/).
- Export it: `export NUTRIENT_API_KEY="pdf_live_..."` (a `pdf_test_...` test key makes real
  provider requests without deducting credits, where test-key access is enabled for the org —
  useful for trying the cookbooks below before wiring in a live key).
- Base URL for `/responses`, `/chat/completions`, `/systemone`, and `/models`:
  `https://api.nutrient.io/ai/v1`.
- Never log, echo, or commit the key. Use it only from trusted backend code — not browsers,
  mobile apps, or client-side code.

## Cookbooks

**Flag a value as implausible, with an attached page image (`noul`, multimodal):**

```bash
curl --fail-with-body https://api.nutrient.io/ai/v1/systemone \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "nutrient-decision",
    "state": {
      "invoice": { "vendor": "Acme Corp", "total": 1024.50, "currency": "USD" },
      "page_1": { "type": "image", "source": "data:image/png;base64,'"$(base64 -i invoice.png)"'" }
    },
    "questions": {
      "amount_reasonable": { "type": "noul", "instructions": "Is the total a plausible invoice amount given the attached page image?" }
    }
  }'
```

**Score severity on an ordered scale (`score`):**

```bash
curl --fail-with-body https://api.nutrient.io/ai/v1/systemone \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "nutrient-decision",
    "state": "Production database is returning 500s for all write requests.",
    "questions": {
      "severity": {
        "type": "score",
        "instructions": "How severe is this incident?",
        "criteria": ["low", "medium", "high", "critical"]
      }
    }
  }'
```

## Good practice

- **Put questions and thresholds in one reviewable file.** A human reviewing your integration
  should find every `instructions`/`criteria` string and every probability threshold in one
  place, not scattered across call sites.
- **Don't take a `noul` probability at face value.** It's a probability, not a verdict — pick a
  threshold from your own evaluation data, and route borderline results to human review instead
  of trusting a single cutoff blindly.
- **Picking the best option? Use highest-confidence `choice`, not a threshold.** If you only need
  "which one", take the label with the highest value in `probabilities`; reserve a confidence
  threshold for "should I act on this at all."
- **Validate assumptions, don't just assert them.** Run a handful of real examples through the
  question before wiring it into production, and check the result lines up with what you'd
  expect — agents are not reliably good at writing the first draft of a question's wording.

## Common issues

- **Wrong model for the capability you need.** `nutrient-decision` supports images in `state`
  and a smaller label/level ceiling (26); `nutrient-systemone` is text-only with a larger ceiling
  (255 labels, 10 score levels). Pick based on what the request actually needs, and confirm via
  `GET /models` rather than assuming.
- **Treating `noul` as a Boolean.** It's a 0–1 probability. Compare against a threshold you
  chose deliberately, not `== 1` or truthiness.
- **Confidence-threshold overuse.** If the goal is just "pick the best option" (routing, best
  guess), use highest-probability `choice`, not an arbitrary confidence floor — a floor only
  makes sense when you need to decide whether to act at all.
- **Invented fields in a request/response.** If the agent references a field or endpoint that
  doesn't match this skill or the [API reference](https://www.nutrient.io/api/reference/ai-gateway/public/),
  the skill may be stale — re-fetch it rather than trusting training-data memory of the API shape.

## Links

- Guides: <https://www.nutrient.io/guides/dws-ai-gateway/>
- Full OpenAPI schema: <https://www.nutrient.io/api/reference/ai-gateway/public/openapi.yml>
- API keys: <https://dashboard.nutrient.io/ai-gateway/api_keys/>
