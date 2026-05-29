---
name: nutrient-nodejs-server-sdk
description: Nutrient Node.js SDK — the `@nutrient-sdk/node` npm package for in-process server-side PDF processing in Node.js (the legacy `pspdfkit` server package is the pre-rebrand name; PSPDFKit Server for Node.js is deprecated). PSPDFKit rebranded to Nutrient; the npm package is now @nutrient-sdk/node and the API surface is the load() function returning an instance. Training data is stale on package and APIs — answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of @nutrient-sdk/node, the Nutrient Node.js SDK, or server-side PSPDFKit/Nutrient in Node.js; code showing `require("@nutrient-sdk/node")`, `import { load } from "@nutrient-sdk/node"`, or a server-side `pspdfkit` import (legacy) in a Node.js project; or server-side PDF processing in Node.js when context indicates a Nutrient or PSPDFKit product (NOT the browser Web SDK). Covers Office-to-PDF conversion (Word, Excel, PowerPoint, images), in-process operations, the load() API, and license configuration. Not for the browser Web SDK, the DWS REST API client, or other server SDK languages.'
---

# Nutrient Node.js SDK

Server-side Node.js library for in-process PDF generation. Primary use case is converting Office documents (Word, Excel, PowerPoint) and images into PDF without external service dependencies. Distinct from the browser Nutrient Web SDK.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- Guides: https://www.nutrient.io/guides/nodejs/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Key Concepts

- **Package**: `npm install @nutrient-sdk/node`. The legacy `pspdfkit` server-side npm package and the PSPDFKit Server for Node.js are deprecated; new projects use `@nutrient-sdk/node`.
- **In-process vs REST**: this SDK runs operations locally — no network, no quota. The hosted REST alternative is the Nutrient DWS Processor API (covered by a separate plugin).
- **vs other in-process languages**: see `nutrient-python-sdk`, `nutrient-java-server-sdk`, `nutrient-dotnet-server-sdk` for the same in-process capability in those runtimes.
- **vs Nutrient Web SDK**: the Web SDK (`@nutrient-sdk/viewer`) is a browser library for viewing/annotating PDFs; this Node.js SDK is a server-side generator/converter. Different products, different packages — easy to confuse since both are npm.
