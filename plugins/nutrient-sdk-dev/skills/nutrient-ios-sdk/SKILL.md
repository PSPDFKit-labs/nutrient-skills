---
name: nutrient-ios-sdk
description: Nutrient iOS SDK — the native Swift/Objective-C PDF SDK for iOS, iPadOS, Mac Catalyst, and visionOS. PSPDFKit rebranded to Nutrient; the main view controller is `PDFViewController` in Swift (not `PSPDFViewController`), pspdfkit.com URLs moved to nutrient.io, and training data is stale on URLs and classes. Answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of PSPDFKit iOS, Nutrient iOS SDK, PDFViewController, PSPDFViewController, or PSPDFDocument; code showing a Swift/Objective-C project with the PSPDFKit CocoaPods, PDFViewController, or PSPDFDocument usage; or PDF viewing/annotation in a native iOS/iPadOS/visionOS app when context indicates a Nutrient or PSPDFKit product. Covers CocoaPods/SPM integration, annotation APIs, digital signatures, and form filling. Not for Android, React Native, Flutter, MAUI, or server-side SDK questions.'
---

# Nutrient iOS SDK

Native Swift/Objective-C SDK for PDF viewing and document interaction on iOS, iPadOS, macOS (Catalyst), and visionOS. Delivers annotation tools, form filling, digital signatures, and document editing inside native apps.

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- API reference: https://www.nutrient.io/api/ios/llms.txt
- Guides: https://www.nutrient.io/guides/ios/llms.txt
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Example Repositories

- Catalog (PDFView, view controller, industry customizations): https://github.com/PSPDFKit/pspdfkit-ios-catalog

## Getting Started

- **Swift Package Manager**: add `https://github.com/PSPDFKit/PSPDFKit-SP` as the package URL — the repo name remains `PSPDFKit-SP` post-rebrand.
- **CocoaPods**: https://www.nutrient.io/sdk/ios/getting-started/ios-cocoapods.md
- **SwiftUI entry type**: `PDFView`
- **UIKit entry class**: `PDFViewController` in Swift. (Named `PSPDFViewController` in Objective-C.)
- **Model entry class**: `Document` in Swift. (Named `PSPDFDocument` in Objective-C.)
