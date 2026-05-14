# PDF Manipulation

Use these patterns when the task is about assembling, slicing, or normalizing PDFs before final delivery operations.

## Merge PDFs

Part order controls merge order:

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F cover=@cover.pdf \
  -F body=@body.pdf \
  -F appendix=@appendix.pdf \
  -F 'instructions={
    "parts": [
      { "file": "cover" },
      { "file": "body" },
      { "file": "appendix" }
    ]
  }' \
  -o packet.pdf
```

## Split or extract page ranges

Use `pages` on a part to carve out a subset:

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document=@document.pdf \
  -F 'instructions={
    "parts": [
      {
        "file": "document",
        "pages": { "start": 0, "end": 4 }
      }
    ]
  }' \
  -o first-five-pages.pdf
```

## Reorder or assemble a packet from ranges

Reuse the same source part with different page ranges to build a new packet:

```json
{
  "parts": [
    { "file": "document", "pages": { "start": 5, "end": 9 } },
    { "file": "document", "pages": { "start": 0, "end": 4 } }
  ]
}
```

## Rotate pages

Use a rotation action when page orientation is wrong:

```json
{
  "parts": [{ "file": "document.pdf" }],
  "actions": [
    {
      "type": "rotate",
      "rotation": 90,
      "pages": [0, 1, 2]
    }
  ]
}
```

## Flatten forms or annotations

Flatten only when the output should stop being interactive:

```json
{
  "parts": [{ "file": "document.pdf" }],
  "actions": [{ "type": "flatten" }]
}
```

## Rules

- Page indexes are zero-based. `end: -1` means the last page.
- Assemble the full packet before watermarking, signing, optimizing, or linearizing.
- Rotate before rasterizing or signing if the source orientation is incorrect.
- Flatten late. It removes editability from forms and many annotation workflows.
- Keep passwords on the affected `part` when slicing or merging encrypted inputs.

## Official docs

- [Processor API overview](https://www.nutrient.io/api/processor-api/)
- [Tools and APIs](https://www.nutrient.io/api/documentation/tools-and-api/)
