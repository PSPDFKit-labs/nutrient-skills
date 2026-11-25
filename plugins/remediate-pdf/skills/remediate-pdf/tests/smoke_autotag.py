#!/usr/bin/env python3
"""Live smoke test + routing/content assertions for remediate-pdf.

Since 1.1 the skill covers auto-tagging, PDF/UA-1 validation (/accessibility/validate_pdfua), and
preparation (conversion and OCR through the Processor API). The content assertions below check
that validation and preparation are routed here, that WCAG is never used as a trigger or claim, and
that the Studio-only fixes are handed off. They run with no API key. The live smoke runs only when
NUTRIENT_ACCESSIBILITY_API_KEY is set.

Routing expectations (this is the canonical routing record for the skill):
  MUST route to remediate-pdf:
    - "auto-tag this PDF for screen readers"
    - "make this document accessible" / "make this Word file accessible"
    - "remediate this PDF for Section 508"
    - "tag this PDF for PDF/UA"
    - "validate PDF/UA" / "does this PDF pass PDF/UA?"
    - "make this scanned PDF accessible"                         (prepare.py --ocr, then autotag)
  MUST NOT route here:
    - "generate an accessible PDF from markdown"                  (route to make-pdf)
    - "convert this PDF to PDF/A", "produce a PDF/UA output via /build", "merge PDFs",
      "sign this document"                                        (document-processor-api)

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


# --- validation and preparation routing ----------------------------------------------------
def test_description_routes_validation_but_not_wcag():
    desc = _frontmatter_description(SKILL_MD.read_text())
    assert "validate" in desc, "description must route PDF/UA validation here"
    assert "pdf/ua-1" in desc
    assert "wcag" not in desc, "description must not use WCAG as a routing trigger"


def test_skill_documents_all_three_scripts_and_studio_handoff():
    body = SKILL_MD.read_text()
    for script in ["autotag.py", "validate.py", "prepare.py"]:
        assert f"scripts/{script}" in body, f"{script} not documented"
        assert (SKILL_DIR / "scripts" / script).is_file(), f"{script} missing"
    assert "isValid" in body, "must tell agents to read isValid, not the HTTP status"
    assert "Accessibility Studio" in body, "Studio-only fixes must be handed off"


def test_registration_lists_capabilities_and_verifier():
    for f in (README, AGENTS):
        line = next(l for l in f.read_text().splitlines() if "remediate-pdf" in l).lower()
        for term in ["auto-tag", "validat", "ocr", "verify"]:
            assert term in line, f"{f.name}: {term!r} missing from the remediate-pdf entry"


# --- positive routing surface ---------------------------------------------------------------
def test_description_has_autotag_routing_terms():
    desc = _frontmatter_description(SKILL_MD.read_text())
    for term in ["auto-tag", "accessible", "pdf/ua", "section 508"]:
        assert term in desc, f"missing positive routing term: {term}"


def test_disambiguation_present():
    body = SKILL_MD.read_text().lower()
    assert "document-processor-api" in body
    assert "pdf/a" in body  # negative routing target named


def test_bundled_verifier_in_sync_with_make_pdf():
    """Repo-layout only: the bundled verify-pdf.py must match make-pdf's copy byte-for-byte."""
    ours = SKILL_DIR / "scripts" / "verify-pdf.py"
    theirs = REPO_ROOT / "plugins" / "make-pdf" / "skills" / "make-pdf" / "scripts" / "verify-pdf.py"
    assert ours.is_file(), "bundled verify-pdf.py missing"
    if not theirs.is_file():
        print("SKIP test_bundled_verifier_in_sync_with_make_pdf (installed layout)")
        return
    assert ours.read_bytes() == theirs.read_bytes(), (
        "verify-pdf.py copies diverged — sync plugins/make-pdf and plugins/remediate-pdf"
    )


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
