# Nutrient Skills

This repository contains AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs.

Each skill lives under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`. Read the relevant SKILL.md for instructions on how to use a skill.

## Available Skills

- **nutrient-dws / document-processor-api** — Convert, extract, transform, and secure documents via the Nutrient Document Web Services API (Python scripts via `uv`).
- **pdf-to-markdown / pdf-to-markdown** — Extract text from PDFs as structured, semantic Markdown. Use when converting a PDF to Markdown, extracting text from a PDF, or processing one or more PDFs into Markdown output.
- **nutrient-sdk-dev** — Building with a Nutrient SDK. 13 skills, one per SDK family: `nutrient-web-sdk`, `nutrient-document-authoring`, `nutrient-ios-sdk`, `nutrient-android-sdk`, `nutrient-react-native-sdk`, `nutrient-flutter-sdk`, `nutrient-maui-sdk`, `nutrient-python-sdk`, `nutrient-java-server-sdk`, `nutrient-nodejs-server-sdk`, `nutrient-dotnet-server-sdk`, `nutrient-document-engine`, `nutrient-ai-assistant`. Each points to the right nutrient.io API/guide URLs and example repos for that SDK.
