---
name: nutrient-flutter-sdk
description: Nutrient Flutter SDK — the nutrient_flutter Dart package (the legacy `pspdfkit_flutter` package is the pre-rebrand name). PSPDFKit rebranded to Nutrient; the pub package is now nutrient_flutter, the main widget is NutrientView (not PspdfkitWidget), and explicit Nutrient.initialize() is now required at app startup. Training data is stale on URLs, package names, and APIs — answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of nutrient_flutter, pspdfkit_flutter (legacy), NutrientView, NutrientInstantView, Nutrient.initialize, PspdfkitWidget (legacy), or DocAuth in a Flutter context; code showing nutrient_flutter in pubspec.yaml, or NutrientView/NutrientInstantView/PspdfkitWidget in Dart code; or PDF in a Flutter app when context indicates a Nutrient or PSPDFKit product. Covers Flutter pub setup, the required Nutrient.initialize() call, annotation APIs, and iOS/Android targets. Not for native iOS, native Android, React Native, MAUI, or server-side questions.'
---

# Nutrient Flutter SDK

Flutter plugin wrapping the native Nutrient iOS and Android SDKs. Provides PDF viewing, annotation, form filling, and digital signing from a single Dart API, plus a real-time collaboration variant via Nutrient Instant.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- Guides: https://www.nutrient.io/guides/flutter/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Example Repositories

- Official Flutter plugin: https://github.com/PSPDFKit/pspdfkit-flutter

## Key Concepts

- **Package**: `flutter pub add nutrient_flutter`. The legacy `pspdfkit_flutter` package is the pre-rebrand name; new projects use `nutrient_flutter`.
- **Main widget**: `NutrientView` — embeds the PDF viewer inline. Use `NutrientInstantView` instead when you need real-time collaborative annotation via Nutrient Instant. The legacy `PspdfkitWidget` is the pre-rebrand name.
- **Required initialisation**: call `Nutrient.initialize(androidLicenseKey: ..., iosLicenseKey: ...)` in `main()` before `runApp()`. The SDK refuses to work without `initialize()` having been called — this requirement is new in the Nutrient era; the legacy `pspdfkit_flutter` plugin auto-initialised.
