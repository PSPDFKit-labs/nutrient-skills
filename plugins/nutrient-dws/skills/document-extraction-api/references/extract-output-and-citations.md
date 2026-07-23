# `/extraction/extract` output and citations

`scripts/extract.py` writes the full JSON response to `--out` and prints a short summary. This
note describes the response shape so you can consume it.

## Response shape

```json
{
  "output": {
    "data":     { /* your schema's fields, with their extracted values */ },
    "metadata": { /* per-field citations, MIRRORING the structure of output.data */ },
    "pages":    [ /* page dimensions, used to interpret citation coordinates */ ]
  },
  "metrics": { "processingTimeMs": 0, "pagesProcessed": 0 },
  "usage":   { "data_extraction_credits": { "cost": 0, "remainingCredits": 0 } }
}
```

- **`output.data`** — the values for the fields you defined in your schema. Field order matches
  your schema (key order is preserved end to end).
- **`output.metadata`** — per-field citations. It **mirrors the structure of `output.data`**: a
  nested field in `data` has its citation at the same path in `metadata`. Each citation grounds
  a value to a region on a page (coordinates interpreted against `output.pages`). This object is
  **empty** when citations are disabled (`--no-citations`).
- **`usage.data_extraction_credits`** — the authoritative cost (parse stage + the flat +6
  cr/page extract surcharge). The script prints this after the call.

## Notes

- Citations are **on by default** (`options.includeCitations: true`); pass `--no-citations` for a
  smaller response (empty `metadata`). Note: the +6 cr/page extract surcharge is flat, so
  disabling citations shrinks the payload but does not lower the credit cost.
- To walk citations for nested fields, traverse `output.data` and `output.metadata` in parallel
  by the same key path — do not assume a flat map.
- Client-side the script validates only the unambiguous limits (root `object`, ≤ 32 KB UTF-8,
  instructions ≤ 10,000 chars). Finer limits (schema node count and depth) are enforced by the
  server, which returns precise `validation_error` paths the script surfaces verbatim.

## Docs

- Extract guide: <https://www.nutrient.io/guides/dws-data-extraction/extract/>
- API overview: <https://www.nutrient.io/api/data-extraction-api/>
- Pricing (parse + 6 cr/page): <https://www.nutrient.io/api/pricing/data-extraction-api/>
