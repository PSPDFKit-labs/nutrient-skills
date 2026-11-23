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
  "usage":   { "global_usd": { "cost": "0.015", "currency": "USD" } }
}
```

- **`output.data`** — the values for the fields you defined in your schema. Field order matches
  your schema (key order is preserved end to end).
- **`output.metadata`** — per-field citations. It **mirrors the structure of `output.data`**: a
  nested field in `data` has its citation at the same path in `metadata`. Each citation grounds
  a value to a region on a page (coordinates interpreted against `output.pages`). This object is
  **empty** when citations are disabled (`--no-citations`).
- **`usage.global_usd.cost`** — the billed cost for USD plans. When present,
  `usage.price_composition` breaks it into parse and extract components. For legacy credit
  plans, read `usage.data_extraction_credits.cost`. The bundled helper prints the legacy
  credit summary when present and saves the full response to `--out`.

## Notes

- Citations are **on by default** (`options.includeCitations: true`). Passing `--no-citations`
  returns empty `metadata` and leaves pricing unchanged.
- To walk citations for nested fields, traverse `output.data` and `output.metadata` in parallel
  by the same key path — do not assume a flat map.
- Client-side the script validates only the unambiguous limits (root `object`, ≤ 32 KB UTF-8,
  instructions ≤ 10,000 chars). Finer limits (schema node count and depth) are enforced by the
  server, which returns precise `validation_error` paths the script surfaces verbatim.

## Docs

- Extract guide: <https://www.nutrient.io/guides/dws-data-extraction/extract/>
- API overview: <https://www.nutrient.io/api/data-extraction-api/>
- Pricing: <https://www.nutrient.io/guides/dws-data-extraction/pricing.md>
