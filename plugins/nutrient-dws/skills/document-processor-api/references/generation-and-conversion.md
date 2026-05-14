# Generation and Conversion

Use these patterns when the main task is to generate a new document or convert an existing one into another format.

## HTML to PDF generation

Upload the HTML file and reference it through `parts[].html`.

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F index.html=@index.html \
  -F 'instructions={"parts":[{"html":"index.html"}]}' \
  -o result.pdf
```

With layout options:

```json
{
  "parts": [{ "html": "index.html" }],
  "output": {
    "type": "pdf",
    "layout": {
      "orientation": "landscape",
      "size": "A4",
      "margin": { "top": 20, "bottom": 20, "left": 15, "right": 15 }
    }
  }
}
```

## Remote URL generation or conversion

When the input already lives at a stable remote URL, send a JSON request and use `file.url`:

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

Use this pattern when you want server-side fetches and do not need to upload a local file first.

## Office to PDF

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.docx=@document.docx \
  -F 'instructions={"parts":[{"file":"document.docx"}]}' \
  -o result.pdf
```

Supported common inputs: `docx`, `xlsx`, `pptx`, `doc`, `xls`, `ppt`, `odt`, `ods`, `odp`, `rtf`

## Image to PDF

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F photo.jpg=@photo.jpg \
  -F 'instructions={"parts":[{"file":"photo.jpg"}]}' \
  -o result.pdf
```

Supported common images: `jpg`, `jpeg`, `png`, `gif`, `webp`, `tiff`, `bmp`

## PDF to Office

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"output":{"type":"docx"}}' \
  -o result.docx
```

Supported common outputs: `docx`, `xlsx`, `pptx`

## PDF to image

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf","pages":{"start":0,"end":0}}],"output":{"type":"png","dpi":150}}' \
  -o page.png
```

Useful output options:

| Option | Meaning |
|--------|---------|
| `type` | `png`, `jpeg`, or `webp` |
| `dpi` | Resolution target |
| `width` / `height` | Explicit pixel size |

## Generation and conversion rules

- Use HTML generation when you control the markup and need stable, reproducible output.
- Use remote URL requests when the source already exists online and you want to avoid local uploads.
- Use `output.type` for direct conversions. Do not create unnecessary `actions` for simple format changes.
- For paginated image output, render only the pages you need.

## Official docs

- [PDF generator / converter overview](https://www.nutrient.io/api/pdf-converter-api/)
- [URL to PDF API](https://www.nutrient.io/api/url-to-pdf-api/)
