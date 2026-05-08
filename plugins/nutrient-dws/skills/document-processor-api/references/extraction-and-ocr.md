# Extraction and OCR

Use these patterns when the goal is to pull machine-readable data from PDFs or scans.

## Extract plain text

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"output":{"type":"text"}}' \
  -o extracted.txt
```

## Extract tables

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"extraction","strategy":"tables"}],"output":{"type":"xlsx"}}' \
  -o tables.xlsx
```

Common structured outputs: `xlsx`, `json`, `xml`, `csv`

## Extract key-value pairs

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"extraction","strategy":"key-values"}],"output":{"type":"json"}}' \
  -o pairs.json
```

## Basic OCR

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F scanned.pdf=@scanned.pdf \
  -F 'instructions={"parts":[{"file":"scanned.pdf"}],"actions":[{"type":"ocr","language":"english"}]}' \
  -o searchable.pdf
```

## Multi-language OCR

```json
{
  "parts": [{ "file": "scanned.pdf" }],
  "actions": [{ "type": "ocr", "language": ["english", "german", "french"] }]
}
```

## OCR on images

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F scan.jpg=@scan.jpg \
  -F 'instructions={"parts":[{"file":"scan.jpg"}],"actions":[{"type":"ocr","language":"english"}]}' \
  -o searchable.pdf
```

## OCR languages

Common OCR languages include:

- `english`
- `german`
- `french`
- `spanish`
- `italian`
- `portuguese`
- `dutch`
- `swedish`
- `polish`
- `czech`
- `turkish`
- `japanese`
- `korean`
- `chinese-simplified`
- `chinese-traditional`
- `arabic`
- `hebrew`
- `hindi`
- `russian`

## OCR and extraction rules

- OCR before extraction when text is image-only, unselectable, or suspiciously sparse.
- Tables and key-values benefit from cleaner scans and correct page orientation.
- For multilingual inputs, pass an array of languages rather than guessing a single language.
- If OCR quality is poor, fix source orientation and scan quality before retrying.

## Official docs

- [Data extraction overview](https://www.nutrient.io/api/data-extraction-api/)
- [Processor API overview](https://www.nutrient.io/api/processor-api/)
