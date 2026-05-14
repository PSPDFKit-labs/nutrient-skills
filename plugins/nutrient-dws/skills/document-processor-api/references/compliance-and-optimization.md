# Compliance and Optimization

Use these patterns when the required output is archival, accessible, or tuned for delivery performance.

## PDF/A archival conversion

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document=@document.pdf \
  -F 'instructions={
    "parts": [
      {
        "file": "document"
      }
    ],
    "output": {
      "type": "pdfa",
      "conformance": "pdfa-2a",
      "vectorization": true,
      "rasterization": true
    }
  }' \
  -o result.pdf
```

Supported PDF/A targets include:

- `pdfa-1a`, `pdfa-1b`
- `pdfa-2a`, `pdfa-2u`, `pdfa-2b`
- `pdfa-3a`, `pdfa-3u`, `pdfa-3b`
- `pdfa-4`, `pdfa-4e`, `pdfa-4f`

### PDF/A caveat

To achieve conformance, conversion may vectorize or rasterize content. That can remove live text and font information, so later OCR may be needed.

## PDF/UA auto-tagging

Dedicated endpoint:

```bash
curl -X POST https://api.nutrient.io/processor/pdfua \
  -H "Content-Type: application/pdf" \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  --data-binary @document.pdf \
  -o result.pdf
```

Equivalent `/build` workflow:

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document=@document.pdf \
  -F 'instructions={
    "parts": [
      {
        "file": "document"
      }
    ],
    "output": {
      "type": "pdfua"
    }
  }' \
  -o result.pdf
```

### PDF/UA rules

- PDF/UA is an accessibility target, not just a format conversion.
- Clean born-digital PDFs generally tag better than rasterized or flattened inputs.
- Structured HTML sources also tend to produce better accessibility outcomes than image-only content.
- Validate final outputs with your required checker when accessibility compliance is contractual.

## PDF optimization and linearization

Linearize a PDF for fast web viewing:

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document=@document.pdf \
  -F 'instructions={
    "parts": [
      {
        "file": "document"
      }
    ],
    "output": {
      "type": "pdf",
      "optimize": {
        "linearize": true
      }
    }
  }' \
  -o result.pdf
```

Optimization with compression controls:

```json
{
  "parts": [{ "file": "document" }],
  "output": {
    "type": "pdf",
    "optimize": {
      "disableImages": false,
      "mrcCompression": true,
      "imageOptimizationQuality": 2,
      "linearize": true
    }
  }
}
```

### Optimization rules

- Linearize only for delivery PDFs meant for network viewing.
- Optimize before signatures when possible. Treat signed PDFs as immutable delivery artifacts.
- Compression changes should be validated visually when image quality matters.

## Official docs

- [PDF to PDF/A API](https://www.nutrient.io/api/pdf-to-pdfa-api/)
- [PDF/UA auto-tagging API](https://www.nutrient.io/api/pdfua-auto-tagging-api/)
- [Optimization API](https://www.nutrient.io/api/document-optimization-api/)
- [PDF linearization API](https://www.nutrient.io/api/pdf-linearization-api/)
