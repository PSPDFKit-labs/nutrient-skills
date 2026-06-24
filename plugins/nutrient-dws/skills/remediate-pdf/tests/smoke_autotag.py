#!/usr/bin/env python3
"""Live smoke test + auto-tag-only routing/content assertions for remediate-pdf.

This skill ships in the AUTO-TAG-ONLY variant (U7 gate decision: no DWS Accessibility validation
endpoint exists yet). The content assertions below enforce that the skill does not advertise
validation routing or carry an autotag->validate ordered-workflow recipe (R17). They run with no
API key. The live smoke runs only when NUTRIENT_ACCESSIBILITY_API_KEY is set.

Routing expectations (this is the canonical routing record for the skill):
  MUST route to remediate-pdf:
    - "auto-tag this PDF for screen readers"
    - "make this document accessible"
    - "remediate this PDF for Section 508"
    - "tag this PDF for PDF/UA"
  MUST NOT route here (auto-tag-only variant — no validation endpoint on this API):
    - "validate PDF/UA compliance" / "check WCAG accessibility"   (route to make-pdf's verify-pdf.py)
    - "generate an accessible PDF from markdown"                  (route to make-pdf)
  MUST NOT route here (belong to document-processor-api):
    - "convert this PDF to PDF/A", "produce a PDF/UA output via /build", "merge PDFs",
      "sign this document"

Run: `python3 smoke_autotag.py`
"""

import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[5]
SKILL_MD = SKILL_DIR / "SKILL.md"
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample.pdf"


def _frontmatter_description(md_text: str) -> str:
    fm = re.match(r"^---\n(.*?)\n---\n", md_text, re.S).group(1)
    m = re.search(r"description:\s*>-\n((?:\s{2,}.*\n?)+)", fm)
    return (m.group(1) if m else fm).lower()


# --- R17: auto-tag-only — no validation routing, no ordered-workflow recipe ------------------
def test_description_has_no_validation_trigger():
    desc = _frontmatter_description(SKILL_MD.read_text())
    assert "validate" not in desc, "description must not advertise validation (auto-tag-only)"
    assert "wcag" not in desc, "description must not use WCAG as a routing trigger here"


def test_no_autotag_then_validate_recipe():
    body = SKILL_MD.read_text().lower()
    for pat in [r"then\s+run\s+validate", r"then\s+validate", r"validate\.py\s+on\s+the",
                r"autotag\.py\s+first,\s*then"]:
        assert not re.search(pat, body), f"ordered-workflow recipe present: {pat!r}"


def test_registration_marks_autotag_only_with_verifier():
    for f in (README, AGENTS):
        line = next(l for l in f.read_text().splitlines() if "remediate-pdf" in l)
        assert "auto-tag" in line.lower(), f"{f.name}: auto-tag-only marker missing"
        assert "verify" in line.lower(), f"{f.name}: verifier pointer missing"


# --- positive routing surface ---------------------------------------------------------------
def test_description_has_autotag_routing_terms():
    desc = _frontmatter_description(SKILL_MD.read_text())
    for term in ["auto-tag", "accessible", "pdf/ua", "section 508"]:
        assert term in desc, f"missing positive routing term: {term}"


def test_disambiguation_present():
    body = SKILL_MD.read_text().lower()
    assert "document-processor-api" in body
    assert "pdf/a" in body  # negative routing target named


# --- live smoke (requires NUTRIENT_ACCESSIBILITY_API_KEY) ------------------------------------
def test_live_autotag():
    if not os.environ.get("NUTRIENT_ACCESSIBILITY_API_KEY"):
        print("SKIP test_live_autotag (NUTRIENT_ACCESSIBILITY_API_KEY not set)")
        return
    out = "/tmp/smoke-at-tagged.pdf"
    r = subprocess.run(
        ["uv", "run", "scripts/autotag.py", "--input", "tests/fixtures/sample.pdf", "--output", out],
        cwd=str(SKILL_DIR), capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == 0, f"autotag failed: {r.stderr}"
    data = Path(out).read_bytes()
    assert data[:4] == b"%PDF", "output is not a PDF"
    assert "page" in r.stderr.lower(), "quota/page note missing from stderr"
    # never leak the key
    key = os.environ["NUTRIENT_ACCESSIBILITY_API_KEY"]
    assert key not in (r.stdout + r.stderr), "API key leaked into output!"


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
