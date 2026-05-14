# Workflow Recipes

Use these patterns when the task spans more than one DWS feature and ordering matters.

## 1. Scan to searchable text

Goal: take an image-only PDF and produce both a searchable PDF and extracted text.

Recommended sequence:

1. OCR the source PDF into a searchable PDF.
2. Extract text from the searchable result.

Reasoning: OCR improves extraction quality and gives you a reusable intermediate artifact.

## 2. Scan to redacted delivery PDF

Goal: redact a scanned document and deliver a shareable PDF.

Recommended sequence:

1. OCR
2. Preset or regex redaction
3. Optional watermark
4. Optional optimization or linearization
5. Signature last, if required

Reasoning: OCR enables reliable matching, and signatures should only happen after all content mutations are complete.

## 3. HTML report to archival PDF

Goal: generate a PDF from structured content and archive it.

Recommended sequence:

1. Generate PDF from HTML
2. Convert the result to PDF/A
3. Validate the archival output in your downstream compliance workflow if required

Reasoning: HTML generation gives you better structure control than post-hoc browser printing, and PDF/A should be treated as a final archival artifact.

## 4. Existing PDF to accessible PDF/UA

Goal: turn a born-digital PDF into a screen-reader-ready artifact.

Recommended sequence:

1. Start from the cleanest available PDF
2. Run PDF/UA auto-tagging
3. Validate the result with your required accessibility checker

Reasoning: flattened, rasterized, or noisy inputs reduce tagging quality.

## 5. Form packet to signed output

Goal: fill a form, remove interactivity if needed, and sign it.

Recommended sequence:

1. Fill form fields
2. Optional flattening
3. Signature last

Reasoning: signing too early forces a second mutation pass and can invalidate the signed artifact.

## 6. Web delivery PDF

Goal: publish a PDF that streams quickly in viewers.

Recommended sequence:

1. Final content edits
2. Optional compression
3. Linearization
4. Publish to a server that supports byte-range requests

Reasoning: linearization is a delivery concern, not an authoring concern.

## 7. Packet assembly before signing

Goal: merge multiple PDFs, fix page orientation, and produce a final packet for signing or distribution.

Recommended sequence:

1. Merge or reorder the required parts
2. Extract or omit page ranges as needed
3. Optional page rotation
4. Optional flattening
5. Watermark, sign, optimize, or linearize last

Reasoning: assembly and page normalization are still content mutations. Final-artifact operations should happen only after the packet shape is stable.

## Recipe heuristics

- Keep OCR early.
- Keep compliance targets intentional.
- Keep signatures last.
- Treat optimization as a delivery-stage step unless the workflow explicitly needs it earlier.
