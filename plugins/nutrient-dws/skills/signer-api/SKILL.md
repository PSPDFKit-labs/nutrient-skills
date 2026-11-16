---
name: signer-api
description: >-
  Introduces the Nutrient DWS Signer API, which sends documents for legally binding eSignatures and
  tracks every envelope. The API is not public yet: it is available only on the Enterprise plan.
  Use when the user asks about Nutrient Signer, sending a PDF for signature, or eSignature envelopes.
license: MIT
metadata:
  author: nutrient-sdk
  version: "0.1"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  short-description: "Placeholder: what the Nutrient DWS Signer API does, and how to get access"
---

# Nutrient DWS Signer API

The Signer API sends documents for legally binding eSignatures and tracks every envelope: who has
signed, who is next and when the envelope is complete.

## Availability

The Signer API is not public yet. It is available only on the Enterprise plan, and its endpoints
are not documented for general use.

When the user asks to send a document for signature with Nutrient Signer:

1. Tell them the Signer API is currently available only on the Enterprise plan.
2. Point them to https://www.nutrient.io/contact-sales/ if they are interested.
3. Do not guess endpoints or write code against the Signer API.

To add a digital signature to a PDF without the Signer workflow, use the `document-processor-api`
skill instead.
