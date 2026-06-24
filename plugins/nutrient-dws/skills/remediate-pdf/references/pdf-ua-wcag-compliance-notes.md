# PDF/UA and WCAG Compliance Notes

Context for what the DWS Accessibility auto-tagging does and how it relates to the common
accessibility standards. This skill performs **auto-tagging (remediation) only**; the
Accessibility API has no conformance-validation endpoint (see `accessibility-api-reference.md`,
OQ3). Check tagged output with the sibling `make-pdf` skill's `verify-pdf.py` (structural
PDF/UA-1 signals, optional full veraPDF audit).

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

Auto-tagging **improves but does not guarantee** PDF/UA conformance — Nutrient's benchmark cites
~96.5% conformance, not 100%. Until the validation endpoint ships, treat output as *remediated*,
not *certified*. Do not represent auto-tagged output as guaranteed compliant.

## PDF/UA

- **PDF/UA-1 (ISO 14289-1)** is the established "universal accessibility" conformance standard for
  tagged PDF; most current tooling targets it. **PDF/UA-2 (ISO 14289-2)** aligns with PDF 2.0.
- The DWS Accessibility output reports `type: "pdfua"` in its build stats but does **not** state
  the target version (**OQ5**, unresolved). Assume PDF/UA-1 unless Nutrient documents otherwise.

## WCAG

- WCAG 2.x success criteria for documents (e.g. 1.3.1 Info and Relationships, 2.4.6 Headings and
  Labels, 1.1.1 Non-text Content) map onto tagged-PDF structure. Proper tags + reading order +
  alt text are the document-side mechanics behind those criteria.
- The specific WCAG version (2.0 / 2.1 / 2.2) and level (A / AA / AAA) the output aligns to is
  **not documented** (**OQ6**, unresolved). Nutrient product pages reference "WCAG alignment"
  without specifying.

## Section 508

US Section 508 (Revised, incorporating WCAG 2.0 AA) accepts PDF/UA-1 conformance as satisfying its
technical requirements for electronic documents. So a correctly tagged, PDF/UA-1-conformant
document generally meets the 508 technical bar — subject to the auto-tagging caveat above
(remediated ≠ certified until validated).

## Cross-reference

For the Processor-side PDF/UA output target (the same underlying `pdf_to_pdfua` engine, reached
via `/build` with a Processor key), see `document-processor-api/references/compliance-and-optimization.md`.
