#!/usr/bin/env python3
"""Keyless routing + registration assertions for dws-viewer-api (enforces R-01).

These run with no API key. They mechanize the routing-collision check that the smoke-test guide
(smoke-test-guide.md) documents as a manual step, so the skill's core disambiguation purpose —
not colliding with the self-hosted `nutrient-web-sdk` skill — is regression-guarded. The LIVE
upload/session/delete steps stay in smoke-test-guide.md (they need a real key + teardown).

Run: `python3 smoke_viewer.py`
"""

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[5]
SKILL_MD = SKILL_DIR / "SKILL.md"
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
WEB_SDK_MD = REPO_ROOT / "plugins" / "nutrient-sdk-dev" / "skills" / "nutrient-web-sdk" / "SKILL.md"


def _frontmatter(md_text: str) -> dict:
    fm = re.match(r"^---\n(.*?)\n---\n", md_text, re.S).group(1)
    out, key, buf = {}, None, []
    for line in fm.splitlines():
        m = re.match(r"^(\w[\w_]*):\s?(.*)$", line)
        if m and not line.startswith(" "):
            if key:
                out[key] = " ".join(buf).strip()
            key, buf = m.group(1), [m.group(2)]
        elif key:
            buf.append(line.strip())
    if key:
        out[key] = " ".join(buf).strip()
    return out


def _routing_text() -> str:
    fm = _frontmatter(SKILL_MD.read_text())
    return (fm.get("description", "") + " " + fm.get("when_to_use", "")).lower()


# --- positive routing surface ---------------------------------------------------------------
def test_positive_routing_terms_present():
    t = _routing_text()
    for term in ["dws viewer api", "cloud", "session jwt", "viewer session"]:
        assert term in t, f"missing positive routing term: {term!r}"


# --- R-01: disambiguation / negation --------------------------------------------------------
def test_names_both_sibling_products_as_negation():
    t = _routing_text()
    assert "nutrient-web-sdk" in t, "must route the self-hosted WASM viewer to nutrient-web-sdk"
    assert "nutrient-document-engine" in t, "must route self-hosted persistence to document-engine"


def test_nutrientviewer_load_is_qualified_with_session():
    # The only symbol shared with nutrient-web-sdk is NutrientViewer.load; this skill must qualify
    # it with a session token (and route the bare/no-session form away to nutrient-web-sdk).
    t = _routing_text()
    assert "without a dws session" in t or "without a session" in t, \
        "bare NutrientViewer.load (no session) must be routed to nutrient-web-sdk"


def test_no_verbatim_trigger_collision_with_web_sdk():
    # No distinctive multi-word trigger phrase should appear verbatim in both skills' routing text.
    web = _frontmatter(WEB_SDK_MD.read_text())
    web_t = (web.get("description", "") + " " + web.get("when_to_use", "")).lower()
    mine = _routing_text()

    def trigrams(s):
        toks = re.sub(r"[^a-z0-9 ]", " ", s).split()
        return {" ".join(toks[i:i + 3]) for i in range(len(toks) - 2)}

    shared = trigrams(mine) & trigrams(web_t)
    # Disambiguation phrases (each skill naming the other / the package, to route away) are allowed.
    allowed = ("nutrient web sdk", "nutrient document engine", "nutrient sdk viewer",
               "sdk viewer nutrientviewer", "viewer with a", "pdf viewer with")
    collisions = [p for p in shared
                  if any(k in p for k in ("session", "cloud viewer", "viewer session"))
                  and not any(a in p for a in allowed)]
    assert not collisions, f"verbatim trigger collision with nutrient-web-sdk: {collisions}"


# --- registration ---------------------------------------------------------------------------
def test_registered_in_readme_and_agents():
    for f in (README, AGENTS):
        assert "dws-viewer-api" in f.read_text(), f"{f.name}: dws-viewer-api not registered"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
