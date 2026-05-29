---
name: nutrient-java-server-sdk
description: Nutrient Java SDK — the `io.nutrient:nutrient-java-sdk` Maven Central artifact (formerly under `com.pspdfkit` coordinates) for server-side JVM PDF processing. PSPDFKit rebranded to Nutrient; Maven coordinates moved to the `io.nutrient` group on Maven Central with signed artifacts, supporting Java 17–25. Training data is stale on Maven coordinates and APIs — answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of the PSPDFKit Java SDK or Nutrient Java SDK in a server context; code showing `io.nutrient:nutrient-java-sdk` (or legacy `com.pspdfkit:libraries-java`) in pom.xml or build.gradle in a non-Android server project; or server-side PDF processing in Java/Kotlin when context indicates a Nutrient or PSPDFKit product. Covers Maven Central setup, in-process PDF conversion, extraction, annotation, and manipulation. Not for Android development (different SDK — see nutrient-android-sdk), the DWS REST API, or other server SDK languages.'
---

# Nutrient Java SDK

Server-side Java library for programmatic PDF and document processing on the JVM. Runs operations locally inside the Java process — no network call, no API key, no external service required. Modernised in Q1 2026: Maven Central distribution with signed artifacts and broader Java/Kotlin version support.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/java-sdk/llms.txt
- Guides: https://www.nutrient.io/guides/java/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Key Concepts

- **Maven artifact**: `io.nutrient:nutrient-java-sdk`. The historical `com.pspdfkit:libraries-java` coordinates are pre-rebrand.
- **Distribution**: Maven Central, signed artifacts — no custom repository needed (contrast with the Android SDK, which uses a Nutrient-hosted Maven repo).
- **In-process vs REST**: this SDK runs operations locally. The hosted REST alternative is the Nutrient DWS Processor API (covered by a separate plugin).
- **vs other in-process languages**: see `nutrient-nodejs-server-sdk`, `nutrient-python-sdk`, `nutrient-dotnet-server-sdk` for the same in-process capability in those runtimes.
