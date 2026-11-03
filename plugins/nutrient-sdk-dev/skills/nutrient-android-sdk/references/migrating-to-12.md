# Migrating to Nutrient Android SDK 12.x

Use this when an app upgrades from 11.x to 12.0, from 12.0 to 12.1, or from 11.x straight to 12.1. Both releases contain source-breaking changes with no deprecation window, so the app will not compile until they are migrated.

## Sources

Fetch these as Markdown. They are the source of truth; this file only says how to use them.

| Upgrade | Read |
| --- | --- |
| 11.x → 12.0 | https://www.nutrient.io/guides/android/migration-guides/12-migration-guide.md |
| 12.0 → 12.1 | https://www.nutrient.io/guides/android/releases/12-1.md (the "Migration guide" section) |
| Context for either | https://www.nutrient.io/guides/android/releases/12-0.md and https://www.nutrient.io/guides/android/changelog.md |

Going from 11.x to 12.1, apply the 12.0 guide first, then the 12.1 guide. Calling the SDK's async APIs from Java is covered in https://www.nutrient.io/guides/android/best-practices/calling-async-apis-from-java.md.

## Workflow

1. **Find the versions.** Read the current SDK version from the Gradle files (`io.nutrient:nutrient-android-sdk` on Maven Central, or the legacy `io.nutrient:nutrient` on `https://my.nutrient.io/maven`) and confirm the target with the user.
2. **Inventory before editing.** Search the app for every API the relevant guides list, including overrides and interface implementations, not just calls. Group the findings by file.
3. **Confirm each mapping.** Take replacements from the guides, then check the exact overload, imports, nullability and return type against the target SDK, for example with `javap` on the AAR's `classes.jar` in the Gradle cache. Do not invent replacements. Leave a call unchanged and report it when the guides and the SDK disagree, or when no replacement is listed.
4. **Migrate confirmed cases,** keeping unrelated code, names and formatting as they are.
5. **Update the build.** Apply the requirements below, declare dependencies the SDK no longer supplies, and move the dependency to Maven Central if the app still uses the legacy artifact (see the next section).
6. **Compile and run the existing tests.** A successful compile does not prove the behavior is unchanged. Check the behavior changes each guide lists.
7. **Report** what changed, what was deliberately kept, what is unresolved (with file locations), and which checks ran.

## Switch to Maven Central

Since 11.6 the SDK is on Maven Central as `io.nutrient:nutrient-android-sdk`. The legacy `io.nutrient:nutrient` artifact on `https://my.nutrient.io/maven` is only kept for a transition period, so move the app over while upgrading:

```kotlin
dependencies {
    implementation("io.nutrient:nutrient-android-sdk:<version>")
}
```

Then remove the `https://my.nutrient.io/maven` repository from `settings.gradle(.kts)`, unless the app uses the OCR add-on. OCR (`io.nutrient:nutrient-ocr` and its language packs) is not on Maven Central yet, so keep the repository for it. Its POM still depends on the legacy `io.nutrient:nutrient`, so exclude that, or the app gets the SDK's classes twice:

```kotlin
implementation("io.nutrient:nutrient-ocr:<version>") {
    exclude(group = "io.nutrient", module = "nutrient")
}
```

## 11.x → 12.0 at a glance

- **Requirements:** `compileSdk = 37` with `compileSdkMinor = 1`, Kotlin 2.3 or newer, Jetpack Compose 1.12.0.
- **Main toolbar:** the options-menu contract no longer drives it. Replace `onCreateOptionsMenu`, `onPrepareOptionsMenu`, menu XML and `OnMenuItemsGenerateListener` with `setToolbarItemsProvider`, and `onOptionsItemSelected` with `setOnToolbarItemClickListener`. `invalidateOptionsMenu()` becomes `invalidateToolbarItems()`.
- **Contextual toolbars:** the View-based `ContextualToolbar` hierarchy and `ToolbarCoordinatorLayout` are removed. Customize them through `ToolbarCoordinator`.
- **Other areas:** inline search, document title overlay, insets, the annotation inspector color picker (`setCustomColorPickerEnabled` became `setRestrictToAvailableColors`), the settings dialog, Material 3 modal sheets, the document overview grid, and `PdfFragment` and `PdfTabBar` becoming Kotlin classes. Each has its own section in the guide.

## 12.0 → 12.1 at a glance

- **RxJava is gone.** Every method that returned `Single`, `Maybe`, `Completable`, `Observable` or `Flowable` is now `suspend` or returns a `Flow`. The `*RxJava` and `*Blocking` bridges are removed. Ask the user which mode they want before editing:
  - **Boundary only:** keep the app's RxJava and wrap SDK calls with `kotlinx-coroutines-rx3` (`rxSingle`, `rxMaybe`, `rxCompletable`, `asFlowable`, `asObservable`). Check result shapes: some former `Observable` APIs now return a whole list.
  - **Full conversion:** convert the affected call sites to suspend calls and `Flow` collection.
- **Dependencies:** the SDK no longer brings in RxJava. Declare `io.reactivex.rxjava3:rxjava`, `rxandroid`, `kotlinx-coroutines-rx3` or `runtime-rxjava3` if the app still uses them.
- **Interfaces you implement:** `ProgressDataProvider`, `DownloadJob` progress, `PdfOutlineView.DocumentOutlineProvider`, `FilePicker` and the protected `PdfFragment` hooks changed signature. A progress `Flow` must still complete after its final value.
- **Java callers:** Java cannot call `suspend` functions directly. Prefer a synchronous SDK overload where one exists, or a small Kotlin adapter. Use `BuildersKt.runBlocking` only on a worker thread, and type list results as `List<? extends T>`.
- **Theming:** `setMainToolbarColorScheme()`, `NutrientThemeController`, `UiTheme`, `SdkTheme`, `getUiColors()` and `getComposeUiColors()` are deprecated in favor of `setColorScheme()` and `NutrientTheme`. The color scheme classes are no longer data classes, and `SettingsColorScheme` has two new required properties.
- **Smaller changes:** the default `maxZoomScale` is 50, text selection handle colors follow `pspdf__highlightColor`, `DownloadProgressFragment`'s `dialog` is now `downloadDialog`, and Kotlin code calling `Signature.createInkSignature()`, `createStampSignature()` or `ElectronicSignatureOptions` with default arguments must be recompiled.

## Rules for coroutine conversions

- Keep blocking work the app owns on `Dispatchers.IO` or `Dispatchers.Default`. Don't wrap every SDK call in `withContext`; the SDK moves most of its own work off the main thread.
- Rethrow `CancellationException` before a general `catch`.
- An empty `Maybe` skipped its success handler; a nullable suspend result returns `null` and execution continues. Add a null guard.
- Replace `Disposable` and `CompositeDisposable` with jobs or scopes of the same lifetime (`lifecycleScope`, `viewLifecycleOwner.lifecycleScope`, `viewModelScope`). Never introduce `GlobalScope`.
- A coroutine's `finally` also runs on cancellation, unlike `doAfterTerminate`. Don't replace `share()` with `shareIn()` mechanically.
- `RxJavaPlugins.setErrorHandler` doesn't see failures from converted code. Connect them to the app's existing error reporting.
