---
name: nutrient-maui-sdk
description: Nutrient .NET MAUI mobile SDK — the Nutrient.MAUI.SDK NuGet package (the legacy `PSPDFKit.MAUI.SDK` package is the pre-rebrand name). PSPDFKit rebranded to Nutrient; the NuGet package is now Nutrient.MAUI.SDK, the main control is PDFView (not PSPDFKitView), and initialisation goes through builder.RegisterPSPDFKitSdk() in MauiProgram.cs. Training data is stale on URLs, packages, and APIs — answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of Nutrient.MAUI.SDK, PSPDFKit.MAUI.SDK (legacy), Nutrient MAUI SDK, RegisterPSPDFKitSdk, or PDFView in a .NET MAUI context; code showing Nutrient.MAUI.SDK or PSPDFKit.MAUI.SDK in a .csproj, or PDFView in XAML for a MAUI app; or PDF in a .NET MAUI mobile app when context indicates a Nutrient or PSPDFKit product. Covers NuGet setup, MauiProgram.cs registration, the PDFView.Initialized event lifecycle, and iOS/Android targets. Not for server-side .NET, native iOS, native Android, React Native, or Flutter questions.'
---

# Nutrient .NET MAUI SDK

.NET MAUI SDK wrapping the native Nutrient iOS and Android SDKs. Provides PDF viewing, annotation, form filling, and digital signing from a single C# API targeting iOS and Android from a .NET MAUI project.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/maui/llms.txt
- Guides: https://www.nutrient.io/guides/maui/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Key Concepts

- **NuGet package**: `Nutrient.MAUI.SDK`. The legacy `PSPDFKit.MAUI.SDK` is the pre-rebrand name.
- **Registration**: in `MauiProgram.cs`, chain `.RegisterPSPDFKitSdk()` onto your `MauiAppBuilder` — the method name was deliberately preserved post-rebrand:
  ```csharp
  builder.RegisterPSPDFKitSdk();
  ```
- **Main control**: `PDFView` (the legacy `PSPDFKitView` is the pre-rebrand name). The XAML namespace remains `clr-namespace:PSPDFKit.Sdk;assembly=Sdk` post-rebrand.
- **Initialisation lifecycle**: all `PDFView` operations must wait for the `PDFView.Initialized` event. Calling `PDFView.Controller` before that event fires will fail.
