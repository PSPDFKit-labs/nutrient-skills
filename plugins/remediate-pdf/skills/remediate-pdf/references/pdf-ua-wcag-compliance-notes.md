# PDF/UA and WCAG Compliance Notes

Context for what Nutrient Accessibility API auto-tagging and validation cover, and how they relate
to the common accessibility standards. For an offline structural check without an API key, use the
bundled `verify-pdf.py` (structural PDF/UA-1 signals, optional full veraPDF audit).

## What auto-tagging does

Auto-tagging writes a semantic structure tree into the PDF so assistive technology (screen
readers) can navigate it:

- **Headings** (H1–H6), **paragraphs** (P), **lists** (L / LI), and **tables**
  (Table / TR / TD / TH) marked as tagged structure elements.
- **Reading order** normalized so content is announced in logical sequence rather than
  geometric/stream order.
- **Artifact marking** for decorative content (page furniture, rules) so it is skipped by AT.
- Anchor points for **alt text** on figures (the alt text itself is author-supplied; auto-tagging
  establishes the structure, not the descriptions).

Auto-tagging doesn't add a text layer, so image-only scans need OCR first. It improves but does
not guarantee PDF/UA conformance: in Nutrient's March 2026 benchmark of 3,157 files checked with
veraPDF, 96.5 percent passed PDF/UA-1 validation. Treat auto-tagged output as *tagged*, and
validate it before calling it conformant.

## What validation covers

- `validate.py` checks a PDF against **PDF/UA-1 (ISO 14289-1)**, the only profile the API
  supports, and reports every failed machine-testable requirement.
- Many PDF/UA requirements need a person to judge them: whether alt text describes the image,
  whether the reading order is logical, whether tag types and heading levels are right, and
  whether the declared title and language are correct. A pass from the API means the PDF passed
  machine validation, not that it is fully conformant or accessible.
- The API report passes placeholder alt text such as "image"; Accessibility Studio's validation
  warns about it.

## PDF/UA

- **PDF/UA-1 (ISO 14289-1)** is the established "universal accessibility" conformance standard for
  tagged PDF; most current tooling targets it. **PDF/UA-2 (ISO 14289-2)** aligns with PDF 2.0 and
  is not validated by this API.
- PDF/UA-1 requires a document title in the metadata (shown in the title bar) and a declared
  natural language, among other things. Those map to WCAG 2.4.2 Page Titled and 3.1.1 Language of
  Page.

## WCAG

- WCAG 2.x success criteria for documents (e.g. 1.3.1 Info and Relationships, 2.4.6 Headings and
  Labels, 1.1.1 Non-text Content) map onto tagged-PDF structure. Proper tags + reading order +
  alt text are the document-side mechanics behind those criteria.
- Some WCAG criteria are outside PDF/UA validation entirely, such as color contrast (1.4.3) and
  use of color (1.4.1).
- Nutrient doesn't document a WCAG version or level that auto-tagged output aligns to. Don't
  state one.

## Section 508

Revised Section 508 requires electronic documents to meet WCAG 2.0 Level AA. PDF/UA-1 conformance
supports many of those criteria, but it doesn't establish Section 508 conformance on its own; that
needs a human check of the document against WCAG. Don't describe auto-tagged or validated output
as Section 508 compliant.

## Cross-reference

For the Processor-side PDF/UA output target (the same underlying `pdf_to_pdfua` engine, reached
via `/build`), see `document-processor-api/references/compliance-and-optimization.md`.
