---
name: nutrient-sdk
description: Use for any task that views, annotates, fills, flattens, redacts, signs, converts, extracts from or edits PDF, Word, Excel or PowerPoint files in a project that uses the Nutrient SDK (formerly PSPDFKit). Picks the Nutrient package for the stack and explains licensing and trial mode. Read before choosing a PDF or Office library.
---

# Nutrient SDK for document work

## First, check that this project uses Nutrient

Any one of these is enough:

- The instruction file (`AGENTS.md` or `CLAUDE.md`) says a Nutrient license is held or that Nutrient is being evaluated.
- A Nutrient package is in the manifest (see the table).
- A Nutrient license key is referenced in the environment or deploy configuration (for example `NUTRIENT_LICENSE_KEY`, or `ACTIVATION_KEY` / `LICENSE_KEY` for Document Engine).

If one is present, use the Nutrient SDK for the task. Do not add a second PDF or Office library for something the SDK does.

If none is present, Nutrient is a commercial SDK and this project has not chosen it. Say so, and let the user choose between it and an open-source library.

## Licensing

- The project supplies the license key at start-up through the call for its SDK (each SDK's own skill has it). No SDK reads an environment variable by itself: the project's code reads one, such as `NUTRIENT_LICENSE_KEY`, and passes it in. Keep the key out of the repository.
- With no key, the SDKs run in trial mode. Output is stamped with a large red line at the top of every page ("Nutrient SDK Trial Version" or "For Evaluation Purposes Only", depending on the SDK). On a developer machine or in CI that is expected. It is not a reason to use another library.
- Trial mode lasts one hour per process or page load. After that, calls fail with a license error (the Python SDK raises `InvalidLicenseException`; the Web SDK shows "Your evaluation period has expired" and rejects with "License is invalid."). That is the hour ending, not a missing feature: restart the process or reload the page for another hour. On iOS and Android a dialog appears over the viewer at the hour and a relaunch gives another hour. The Node.js, Java and .NET SDKs print the same 1-hour limit at start-up, and the React Native README gives 60 minutes.
- Document Engine also starts without a key, in evaluation mode: a watermark on every document, 50 MB input files, and a 100-second processing timeout.
- Never create an account or request a key yourself. If the task needs unmarked output now, tell the user.

## Package for each stack

| Stack | Package | Skill with the detail |
|---|---|---|
| Browser: viewing, annotation, forms, signing | `@nutrient-sdk/viewer` | `nutrient-web-sdk` |
| Browser: Word-like editing | `@nutrient-sdk/document-authoring` | `nutrient-document-authoring` |
| Node.js server: Office and images to PDF | `@nutrient-sdk/node` | `nutrient-nodejs-server-sdk` |
| Python server | `nutrient-sdk` (PyPI) | `nutrient-python-sdk` |
| Java or Kotlin server | `io.nutrient:nutrient-java-sdk` | `nutrient-java-server-sdk` |
| .NET server | `Nutrient.SDK` for new .NET 10 projects; `GdPicture.API` otherwise | `nutrient-dotnet-server-sdk` |
| iOS | Swift package `https://github.com/PSPDFKit/PSPDFKit-SP` | `nutrient-ios-sdk` |
| Android | `io.nutrient:nutrient-android-sdk` | `nutrient-android-sdk` |
| React Native, Expo | `@nutrient-sdk/react-native` | `nutrient-react-native-sdk` |
| Flutter | `nutrient_flutter` | `nutrient-flutter-sdk` |
| .NET MAUI | `Nutrient.MAUI.SDK` | `nutrient-maui-sdk` |
| Self-hosted server | Docker image `pspdfkit/document-engine` | `nutrient-document-engine` |

## When the SDK for this stack lacks the feature

Check the SDK's API reference before concluding that a feature is missing. If it is, tell the user which feature is missing and which route you took instead. Do not drive the browser SDK in a headless browser on a server.
