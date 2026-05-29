---
name: nutrient-document-authoring
description: Nutrient Document Authoring — the @nutrient-sdk/document-authoring npm package, a WYSIWYG in-browser document editor with page-based, Word-like rich-text editing. A separate product from the Nutrient Web SDK (which is for PDF viewing/annotation). PSPDFKit rebranded to Nutrient; doc URLs moved to nutrient.io, so training data is stale on URLs and APIs. Answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of Nutrient Document Authoring, @nutrient-sdk/document-authoring, DocAuth, createDocAuthSystem, or page-based / WYSIWYG / Word-like document editing in the browser with Nutrient; code showing `import DocAuth from "@nutrient-sdk/document-authoring"` or `createDocAuthSystem()`; or rich-text document creation/editing inside a web app when context indicates a Nutrient product. Covers npm/Vite/CDN setup, the createEditor() API, and supported document formats. Not for PDF viewing or annotation (see nutrient-web-sdk), mobile, server-side SDKs, the DWS API, or Nutrient Document Engine.'
---

# Nutrient Document Authoring

WYSIWYG in-browser document editor — a page-based, Word-like rich-text editing surface that runs entirely in the browser. Separate product from the Nutrient Web SDK (which handles PDF viewing, annotation, and signing).

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/document-authoring/llms.txt
- Guides: https://www.nutrient.io/guides/document-authoring/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Live Demo

- https://document-authoring-demo.pspdfkit.com/sample/

## Key Concepts

- **Package**: `npm i @nutrient-sdk/document-authoring`.
- **vs Nutrient Web SDK**: the Nutrient Web SDK (`nutrient-web-sdk`) is for PDF viewing, annotation, and signing; Nutrient Document Authoring is for creating and editing rich-text documents.
