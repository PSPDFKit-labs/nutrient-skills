# Browser embed guide — DWS Viewer API

Once `viewer-session.py` gives you a `jwt`, the client embed is a single `NutrientViewer.load()`
call with the `session` option. That is the entire browser-side integration for the cloud Viewer
API. This guide is intentionally thin: the server-side work (upload + session mint) is this skill;
**framework integration (React, Vue, Angular, Next.js) belongs to the `nutrient-web-sdk` skill**,
which covers the `@nutrient-sdk/viewer` npm package in depth.

## Minimal embed

```html
<!-- Pin/verify the version against the current SDK release — see the version note below. -->
<script src="https://cdn.cloud.nutrient.io/pspdfkit-web@1.16.1/nutrient-viewer.js"></script>
<div id="viewer" style="width: 100%; height: 600px;"></div>
<script>
  NutrientViewer.load({
    container: document.getElementById("viewer"),
    session: "<jwt from viewer-session.py>",
  });
</script>
```

- The mounting container **must** have an explicit width and height before `load()` is called, or
  initialization fails.
- `session:` is what distinguishes a cloud Viewer API embed from a self-hosted Web SDK embed (which
  uses `document:` + a license key instead). If you are not passing a `session`, you are doing
  self-hosted Web SDK work — use the `nutrient-web-sdk` skill.

## CDN version

The snippet pins `pspdfkit-web@1.16.1` (current at 2026-06-16). This version drifts. Check it
against the current SDK release rather than hard-coding it long-term; the CDN host
(`https://cdn.cloud.nutrient.io/pspdfkit-web@<version>/nutrient-viewer.js`) is stable, the version
segment is not.

## Handling the JWT safely

- The session JWT is a **bearer credential** granting document access until its `exp`. Treat it like
  a password: do not commit it, do not bake it into a client-side source bundle at build time, and
  do not log it. Fetch it from your backend at runtime and hand it to `NutrientViewer.load()`.
- There is no confirmed session-revocation endpoint. A leaked JWT can only be contained by rotating
  the underlying API key and waiting out the current `exp`. Keep TTLs short for sensitive documents.

## Framework integration

For React/Vue/Angular/Next.js/Electron integration of `@nutrient-sdk/viewer`, container lifecycle,
and the standalone-vs-server-backed distinction, use the **`nutrient-web-sdk`** skill. Do not
duplicate those recipes here — the only cloud-Viewer-specific detail is passing `session:` instead
of `document:` + license key.

## llms.txt & references

- Viewer API guides: <https://www.nutrient.io/guides/dws-viewer/llms.txt>
- Getting started (CDN snippet, session flow): <https://www.nutrient.io/guides/dws-viewer/getting-started/>
- Cross-product index: <https://www.nutrient.io/llms.txt>

<!-- TODO: add a DWS Viewer API example repo URL when confirmed. Research did not confirm a public
     example repo specific to the cloud Viewer API (the Web SDK example repos at
     github.com/PSPDFKit are for the self-hosted SDK, not the cloud Viewer API). -->
