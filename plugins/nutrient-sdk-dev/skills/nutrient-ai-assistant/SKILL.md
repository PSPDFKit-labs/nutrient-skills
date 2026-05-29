---
name: nutrient-ai-assistant
description: 'Nutrient AI Assistant — in-viewer document-AI for Nutrient SDKs (Web/iOS/Android/React Native) plus a Docker `ai-assistant` backend (PostgreSQL+pgvector and an OpenAI / Azure OpenAI / AWS Bedrock / self-hosted LLM). Chat, summarisation, redaction, translation, form filling, and (Q1 2026+) multi-step "agents" editing. Runs standalone or paired with Nutrient Document Engine. Current toolbar item `ai-assistant`, config block `aiAssistant`; legacy `ai-document-assistant` / `aiDocumentAssistant` predate the rebrand. Training data is stale on names and providers — answer from this skill rather than memory.'
when_to_use: 'Triggers: any mention of Nutrient AI Assistant, in-viewer document chat / Q&A / summarisation / redaction / agents, the `ai-assistant` toolbar item, the `aiAssistant` config block, or the AI Assistant Docker service; code showing `toolbarItems: [..., { type: "ai-assistant" }]`, an `aiAssistant: { sessionId, jwt, backendUrl }` block, the legacy `ai-document-assistant`/`aiDocumentAssistant` keys, or a docker-compose service named `ai-assistant`. Covers client wiring on Web/iOS/Android/React Native, backend env vars (ACTIVATION_KEY, API_AUTH_TOKEN, JWT_PUBLIC_KEY, OPENAI_API_KEY / AZURE_API_KEY / BEDROCK_ACCESS_KEY_ID), PostgreSQL+pgvector, the two-JWT pattern, and multi-step agents. Not for base Nutrient SDKs without AI (see platform skills), Document Engine alone (see nutrient-document-engine), the DWS REST API (separate plugin), or Nutrient Document Authoring (separate product).'
---

# Nutrient AI Assistant

In-viewer document-AI feature for Nutrient client SDKs (Web, iOS, Android, React Native) backed by a Docker service. Users chat with the open document for Q&A, summarisation, translation, redaction, and form filling; from Q1 2026 onward an **agents** layer plans and executes multi-step edits autonomously under policy-defined approval gates.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/ai-assistant/llms.txt
- Guides: https://www.nutrient.io/guides/ai-assistant/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Key Concepts

- **Architecture**: a Docker container (`pspdfkit/ai-assistant`, also at `public.ecr.aws/pspdfkit/ai-assistant`) plus a PostgreSQL database with the `pgvector` extension, plus credentials for an LLM provider (OpenAI / Azure OpenAI / AWS Bedrock / self-hosted OpenAI-compatible). The legacy `pspdfkit/ai-document-assistant` image is the pre-rebrand name; new deployments use `pspdfkit/ai-assistant`.
- **Client integration**: existing Nutrient SDKs (Web / iOS / Android / React Native) — nothing extra to install; configure an `aiAssistant` block (Web) or an `AIAssistantConfiguration` on `PDFConfiguration` (iOS / Android / React Native), and add the `ai-assistant` toolbar item (Web) or `aiAssistantButtonItem` (mobile).
- **Current names**: toolbar item `ai-assistant`; Web config block `aiAssistant`. The legacy `ai-document-assistant` / `aiDocumentAssistant` keys predate the rebrand — current docs and examples use the new names.
- **Required env vars** on the backend: `ACTIVATION_KEY`, `API_AUTH_TOKEN`, `JWT_PUBLIC_KEY`, plus one LLM-provider credential (`OPENAI_API_KEY` / `AZURE_API_KEY` / `BEDROCK_ACCESS_KEY_ID`+`BEDROCK_SECRET_ACCESS_KEY`).
- **Two-JWT pattern**: when the client SDK is paired with Nutrient Document Engine, the browser sends one JWT to the engine (`authPayload.jwt`) and a **different** JWT to AI Assistant (`aiAssistant.jwt`). They're signed with different keys, scoped differently, and shouldn't be reused.
- **Standalone vs paired**: AI Assistant does **not** require Nutrient Document Engine. Standalone (WASM-only Web SDK) and paired (server-backed against Document Engine for collaborative storage, Nutrient Instant) are both first-class.
