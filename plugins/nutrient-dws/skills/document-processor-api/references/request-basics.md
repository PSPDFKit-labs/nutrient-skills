# Request Basics

Most Nutrient DWS workflows use:

```text
POST https://api.nutrient.io/build
Authorization: Bearer YOUR_API_KEY
```

Use multipart when you are uploading local files. Use JSON when every input is a remote URL.

## Multipart pattern

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document=@document.pdf \
  -F 'instructions={"parts":[{"file":"document"}]}' \
  -o result.pdf
```

## JSON pattern for remote URLs

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -d '{
    "parts": [
      {
        "file": {
          "url": "https://www.nutrient.io/api/assets/downloads/samples/docx/document.docx"
        }
      }
    ]
  }' \
  -o result.pdf
```

## Instructions model

```json
{
  "parts": [
    {
      "file": "document.pdf",
      "pages": { "start": 0, "end": -1 },
      "password": "optional-password"
    }
  ],
  "actions": [
    { "type": "action_type" }
  ],
  "output": {
    "type": "pdf"
  }
}
```

## Core rules

- Multipart field names must match the filenames or symbolic names referenced in `parts`.
- `parts` preserves order. Multiple parts become a merged output unless the selected output type says otherwise.
- `actions` execute in order and mutate the in-flight document.
- `output.type` selects the final artifact type such as `pdf`, `text`, `docx`, `xlsx`, `pptx`, `png`, `pdfa`, or `pdfua`.
- Password-protected inputs need `password` on the relevant part.

## Credits

Check balance:

```bash
curl -X GET https://api.nutrient.io/credits \
  -H "Authorization: Bearer $NUTRIENT_API_KEY"
```

Check usage:

```bash
curl -X GET "https://api.nutrient.io/credits/usage?period=month" \
  -H "Authorization: Bearer $NUTRIENT_API_KEY"
```

## Limits and common errors

### HTTP status codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Invalid instructions or missing required fields |
| `401` | Invalid or missing API key |
| `402` | Insufficient credits |
| `413` | Payload too large |
| `415` | Unsupported media type |
| `422` | Valid request but unsupported or unprocessable content |
| `429` | Rate limited |
| `500` | Server error |

### Common problems

| Problem | Cause | Fix |
|---------|-------|-----|
| `file_not_found` | The symbolic file name in `parts` does not match an uploaded field | Align multipart names and `parts` references |
| Empty extraction | The file is scanned or rasterized | OCR first |
| `password_required` | The PDF is encrypted | Add the password on the part |
| `insufficient_credits` | Batch or AI-heavy workflow exceeded credits | Check balance before the run |

### File limits

- Maximum input file: 100 MB
- Maximum total upload: 500 MB per request
- For faster runs, prefer files below 50 MB when possible

## Official docs

- [API overview](https://www.nutrient.io/api/documentation/developer-guides/api-overview/)
- [Processor API overview](https://www.nutrient.io/api/processor-api/)
