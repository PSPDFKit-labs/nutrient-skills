---
name: nutrient-android-sdk
description: Nutrient Android SDK — the native Kotlin/Java PDF SDK for Android. PSPDFKit rebranded to Nutrient; the Maven Central coordinates are `io.nutrient:nutrient-android-sdk` (formerly `com.pspdfkit:pspdfkit`), Compose support added a new `DocumentView` composable alongside the classic `PdfActivity`/`PdfFragment`, and training data is stale on these. Answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of PSPDFKit Android, Nutrient Android SDK, PdfActivity, PdfFragment, DocumentView (Compose), or `io.nutrient:nutrient`/`com.pspdfkit:pspdfkit` Maven dependency; code showing a Kotlin/Java Android project with the Nutrient Maven repo, PdfActivity, PdfFragment, or DocumentView; or PDF viewing/annotation in a native Android app when context indicates a Nutrient or PSPDFKit product. Covers Maven/Gradle setup, traditional Views vs Jetpack Compose entry points, annotation APIs, digital signatures, form filling, and migrating an app to SDK 12.x (12.0 toolbars, 12.1 coroutines). Not for iOS, React Native, Flutter, MAUI, or server-side SDK questions.'
---

# Nutrient Android SDK

Native Kotlin/Java SDK for PDF viewing and document interaction on Android. Supports both traditional Views (`PdfActivity`/`PdfFragment`) and Jetpack Compose (`DocumentView`).

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/android/llms.txt
- Guides: https://www.nutrient.io/guides/android/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Example Repositories

- Android simple example (PDF viewing and annotation): https://github.com/PSPDFKit/pspdfkit-android-simple-example

## Key Concepts

- **Maven artifact**: `io.nutrient:nutrient-android-sdk:<version>` on Maven Central since 11.6 — the current version is in the guides linked above. The legacy `io.nutrient:nutrient` artifact on the custom repo `https://my.nutrient.io/maven` stays available during the transition, and the OCR add-on (`io.nutrient:nutrient-ocr`) is only there. The historical `com.pspdfkit:pspdfkit` coordinates are pre-rebrand.

## Migrating to 12.x

SDK 12.0 replaced the options-menu toolbars with Jetpack Compose toolbars, and 12.1 replaced the RxJava API with Kotlin coroutines and `Flow`. Both are source-breaking with no deprecation window. Before upgrading an app across either release, read [references/migrating-to-12.md](references/migrating-to-12.md) for the guides to fetch, the workflow, and the rules for coroutine conversions.
