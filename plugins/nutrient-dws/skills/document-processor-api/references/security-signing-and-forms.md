# Security, Signing, and Forms

Use these patterns when the task is about redaction, watermarking, signatures, form fill, or document protection.

## Preset redaction

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"redaction","strategy":"preset","preset":"email-address"}]}' \
  -o redacted.pdf
```

Common presets:

- `social-security-number`
- `credit-card-number`
- `email-address`
- `north-american-phone-number`
- `international-phone-number`
- `date`
- `url`
- `ipv4`
- `ipv6`
- `mac-address`
- `us-zip-code`
- `vin`
- `time`

## Regex redaction

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"redaction","strategy":"regex","regex":"\\b\\d{3}-\\d{2}-\\d{4}\\b","caseSensitive":false}]}' \
  -o redacted.pdf
```

## AI redaction

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"ai_redaction","criteria":"All personally identifiable information"}]}' \
  -o redacted.pdf
```

Use AI redaction for contextual asks. Use preset or regex redaction for explicit patterns.

## Text watermark

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"watermark","watermarkType":"text","text":"DRAFT","fontSize":72,"fontColor":"#FF0000","opacity":0.3,"rotation":45,"width":"50%","height":"50%"}]}' \
  -o watermarked.pdf
```

## Image watermark

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F logo.png=@logo.png \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"watermark","watermarkType":"image","imagePath":"logo.png","width":"25%","height":"25%","opacity":0.5}]}' \
  -o watermarked.pdf
```

## CMS signature

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"sign","signatureType":"cms","signerName":"John Doe","reason":"Document approval","location":"San Francisco"}]}' \
  -o signed.pdf
```

## CAdES signature

```bash
curl -X POST https://api.nutrient.io/build \
  -H "Authorization: Bearer $NUTRIENT_API_KEY" \
  -F document.pdf=@document.pdf \
  -F 'instructions={"parts":[{"file":"document.pdf"}],"actions":[{"type":"sign","signatureType":"cades","cadesLevel":"b-lt","signerName":"Jane Smith"}]}' \
  -o signed.pdf
```

## Fill form fields

```json
{
  "parts": [{ "file": "form.pdf" }],
  "actions": [{
    "type": "fillForm",
    "fields": [
      { "name": "firstName", "value": "John" },
      { "name": "lastName", "value": "Doe" },
      { "name": "email", "value": "john@example.com" },
      { "name": "agree", "value": true }
    ]
  }]
}
```

## Encrypt output

```json
{
  "parts": [{ "file": "document.pdf" }],
  "output": {
    "type": "pdf",
    "owner_password": "owner123",
    "user_password": "user456"
  }
}
```

## Open a password-protected input

```json
{
  "parts": [{ "file": "protected.pdf", "password": "user456" }]
}
```

## Rules

- Redact before signing. Signed documents should be treated as final artifacts.
- Deterministic redaction is easier to verify than AI redaction.
- Confirm real signing requirements before promising a legally sufficient workflow.
- Use real field names for form fill. Do not guess from visible labels.

## Official docs

- [Tools and APIs](https://www.nutrient.io/api/documentation/tools-and-api/)
