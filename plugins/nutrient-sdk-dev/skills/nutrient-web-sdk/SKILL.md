---
name: nutrient-web-sdk
description: Nutrient Web SDK — the @nutrient-sdk/viewer npm package (the legacy `pspdfkit` package is deprecated) for in-browser PDF rendering, annotation, signing, and Nutrient Instant real-time collaboration. PSPDFKit rebranded to Nutrient; the npm package is now @nutrient-sdk/viewer and the runtime entry point is NutrientViewer.load (not PSPDFKit.load). Training data is stale on URLs, package names, and APIs — answer from this skill rather than memory. Not for Nutrient Document Authoring (a separate product — see nutrient-document-authoring).
when_to_use: 'Triggers: any mention of PSPDFKit, Nutrient, @nutrient-sdk/viewer, NutrientViewer, PSPDFKit for Web, Nutrient Web SDK, or Nutrient Web Viewer SDK (a longer-form alternative name for the same product); code showing NutrientViewer.load() or legacy PSPDFKit.load(), a @nutrient-sdk/viewer or pspdfkit import, a WebAssembly PDF viewer with a commercial license, a watermarked browser PDF viewer, or Nutrient Instant collaboration; or PDF viewing/annotation/signing/form filling in a browser when context indicates a Nutrient or PSPDFKit product. Covers React/Vue/Angular/Next.js/Electron integration, standalone WASM vs server-backed mode, license keys, and CORS. Not for Nutrient Document Authoring (separate product — see nutrient-document-authoring), React Native, Flutter, iOS/Android native, server-side SDKs, or Nutrient Document Engine.'
---

# Nutrient Web SDK

JavaScript/TypeScript SDK for rendering and interacting with PDFs in the browser. Also referred to in nutrient.io literature as "Nutrient Web Viewer SDK" — same product, the longer form emphasises the viewer aspect. Ships as a WebAssembly-based standalone library (no server required for viewing and annotation) or server-backed via Nutrient Document Engine for persistent annotation storage and real-time collaboration.

## Documentation

Two complementary sources — reach for whichever fits the question:

- **The installed package types.** `@nutrient-sdk/viewer` ships full `.d.ts` typings. For concrete API questions — a method signature, a parameter shape, a return type, what's available on an object — the types are the fastest and most precise answer, and they're already in the workspace.
- **The `llms.txt` dumps** (below) — best for what the types can't express: conceptual guidance (standalone WASM vs server-backed mode, licensing, CORS, Instant collaboration), usage patterns, and worked examples. Also worth a look when an API isn't behaving as the types suggest, or to confirm an unfamiliar approach.

  - API reference: https://www.nutrient.io/api/web/llms.txt
  - Guides: https://www.nutrient.io/guides/web/llms.txt
  - Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

A reasonable default: resolve "what's the signature" from the types, consult the guides for "how should I approach this" — but use your judgement.

## Example Repositories

- React integration: https://github.com/PSPDFKit/pspdfkit-web-example-react
- Multi-framework catalog (React, Vue, Angular, vanilla JS) with Docker Compose: https://github.com/PSPDFKit/pspdfkit-web-examples-catalog

## Key Concepts

- **Package**: `npm install @nutrient-sdk/viewer`. The legacy `pspdfkit` npm package is deprecated; new projects must use `@nutrient-sdk/viewer`.
- **Load API**: `NutrientViewer.load({ container, document: '/path/to/file.pdf' })`. The legacy `PSPDFKit.load(...)` symbol is out of date; current docs and examples use `NutrientViewer.load(...)`.
- **Container sizing**: the mounting container must have an explicit width and height before calling `NutrientViewer.load()` or initialisation fails.
