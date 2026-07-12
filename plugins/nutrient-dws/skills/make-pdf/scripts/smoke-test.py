#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py[linkify,plugins]", "pikepdf"]
# ///

import importlib.util
import re
import sys
import tempfile
from pathlib import Path

import pikepdf


sys.dont_write_bytecode = True
SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).with_name("make-pdf.py")
VERIFY_SCRIPT_PATH = Path(__file__).with_name("verify-pdf.py")


def import_make_pdf():
    spec = importlib.util.spec_from_file_location("make_pdf", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_pdf"] = module
    spec.loader.exec_module(module)
    return module


def import_verify_pdf():
    spec = importlib.util.spec_from_file_location("verify_pdf", VERIFY_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {VERIFY_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_pdf"] = module
    spec.loader.exec_module(module)
    return module


def assert_contains(value: str, needle: str, label: str) -> None:
    if needle not in value:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    make_pdf = import_make_pdf()
    verify_pdf = import_verify_pdf()
    sample_path = SKILL_DIR / "assets" / "sample" / "sample.md"
    markdown = sample_path.read_text(encoding="utf-8")
    failures: list[str] = []
    checks = 0

    for template in ("document", "memo"):
        for theme in ("light", "dark"):
            checks += 1
            try:
                template_html = make_pdf.load_template(template)
                theme_css = make_pdf.load_theme(theme)
                rendered, metadata = make_pdf.compose_markdown_html(
                    markdown,
                    template_html,
                    theme_css,
                    {"template": template, "theme": theme},
                )
                assert metadata["template"] == template
                assert metadata["theme"] == theme
                assert_contains(rendered, "Quarterly Operating Review", "sample title")
                assert_contains(rendered.lower(), "<html", "opening html tag")
                assert_contains(rendered.lower(), "</html>", "closing html tag")
                if "{{" in rendered:
                    raise AssertionError("unreplaced template placeholder")
                assert_contains(rendered, "<table>", "GFM table")
                assert_contains(rendered, "<h2>Performance Summary</h2>", "body heading survives")
                if "<pre>" not in rendered and "<code>" not in rendered:
                    raise AssertionError("missing code block markup")
                assert_contains(
                    rendered,
                    f"nutrient-make-pdf-theme: {theme}",
                    "theme CSS marker",
                )
            except Exception as e:
                failures.append(f"{template}/{theme}: {e}")

    checks += 1
    try:
        template_html = make_pdf.load_template("memo")
        theme_css = make_pdf.load_theme("light")
        rendered, metadata = make_pdf.compose_markdown_html(
            markdown,
            template_html,
            theme_css,
            {
                "title": "CLI Override Title",
                "template": "memo",
                "theme": "light",
            },
        )
        if metadata["title"] != "CLI Override Title":
            raise AssertionError("CLI title override did not beat frontmatter")
        if metadata["template"] != "memo":
            raise AssertionError("CLI template override did not beat frontmatter")
        if metadata["theme"] != "light":
            raise AssertionError("CLI theme override did not beat frontmatter")
        assert_contains(
            rendered,
            "<title>CLI Override Title</title>",
            "rendered CLI title override",
        )
    except Exception as e:
        failures.append(f"override precedence: {e}")

    checks += 1
    try:
        template_html = make_pdf.load_template("document")
        theme_css = make_pdf.load_theme("light")
        literal_markdown = """# Literal placeholders

```text
{{name}}
```

Literal {{styles}} stays in the body.
"""
        rendered, _ = make_pdf.compose_markdown_html(
            literal_markdown,
            template_html,
            theme_css,
        )
        assert_contains(rendered, "{{name}}", "literal code-fence placeholder")
        assert_contains(rendered, "{{styles}}", "literal body placeholder")
        if rendered.count("nutrient-make-pdf-theme: light") != 1:
            raise AssertionError("theme CSS was injected more than once")
    except Exception as e:
        failures.append(f"literal placeholders: {e}")

    checks += 1
    try:
        thematic_breaks = """---
This is Markdown content, not metadata.

It must remain between both thematic breaks.
---

Trailing content must remain too.
"""
        metadata, body = make_pdf.parse_frontmatter(thematic_breaks)
        if metadata:
            raise AssertionError("invalid frontmatter produced metadata")
        if body != thematic_breaks:
            raise AssertionError("invalid frontmatter did not preserve all content")
    except Exception as e:
        failures.append(f"thematic-break preservation: {e}")

    checks += 1
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            bom_path = Path(tmpdir) / "bom.md"
            bom_path.write_bytes(b"\xef\xbb\xbf---\ntitle: BOM Title\n---\n\nBody.\n")
            metadata, body = make_pdf.parse_frontmatter(make_pdf.read_text(bom_path))
        if metadata.get("title") != "BOM Title":
            raise AssertionError("BOM-prefixed frontmatter title was not parsed")
        assert_contains(body, "Body.", "BOM document body")
    except Exception as e:
        failures.append(f"BOM frontmatter: {e}")

    for template in ("document", "memo"):
        checks += 1
        try:
            rendered, metadata = make_pdf.compose_markdown_html(
                "Body without metadata or a heading.\n",
                make_pdf.load_template(template),
                make_pdf.load_theme("light"),
                {"template": template, "theme": "light"},
                fallback_title="empty-file",
            )
            if metadata["title"] != "empty-file":
                raise AssertionError("filename-stem title fallback was not used")
            assert_contains(rendered, "<title>empty-file</title>", "non-empty title element")
            assert_contains(rendered, "<h1>empty-file</h1>", "non-empty cover heading")
            if re.search(r"<h1>\s*</h1>", rendered):
                raise AssertionError("empty cover heading was emitted")
            if re.search(r'<p class="[^"]+">\s*</p>', rendered):
                raise AssertionError("empty cover metadata paragraph was emitted")
        except Exception as e:
            failures.append(f"{template} empty metadata: {e}")

    checks += 1
    try:
        rendered, metadata = make_pdf.compose_markdown_html(
            "Intro paragraph.\n\n# First Heading\n\n# Second Heading\n",
            make_pdf.load_template("document"),
            make_pdf.load_theme("light"),
            fallback_title="filename-fallback",
        )
        if metadata["title"] != "First Heading":
            raise AssertionError("title did not fall back to the first ATX h1")
        assert_contains(rendered, "<title>First Heading</title>", "first h1 title fallback")
    except Exception as e:
        failures.append(f"first h1 title fallback: {e}")

    checks += 1
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            accessible_path = tmp_path / "accessible.pdf"
            bare_path = tmp_path / "bare.pdf"

            with pikepdf.new() as pdf:
                pdf.add_blank_page(page_size=(72, 72))
                pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
                pdf.Root.StructTreeRoot = pikepdf.Dictionary(
                    Type=pikepdf.Name.StructTreeRoot
                )
                pdf.Root.Lang = "en-US"
                pdf.Root.ViewerPreferences = pikepdf.Dictionary(
                    DisplayDocTitle=True
                )
                with pdf.open_metadata() as metadata:
                    metadata["pdfuaid:part"] = "1"
                    metadata["dc:title"] = "Accessible smoke test"
                pdf.save(accessible_path)

            with pikepdf.new() as pdf:
                pdf.add_blank_page(page_size=(72, 72))
                pdf.save(bare_path)

            accessible_results = [
                *verify_pdf.check_common(accessible_path),
                *verify_pdf.check_pdfua(accessible_path),
            ]
            if not all(result.passed for result in accessible_results):
                failed = [
                    result.name for result in accessible_results if not result.passed
                ]
                raise AssertionError(
                    f"accessible PDF failed structural checks: {', '.join(failed)}"
                )

            bare_pdfua = {
                result.name: result for result in verify_pdf.check_pdfua(bare_path)
            }
            if bare_pdfua["pdfuaid:part"].passed:
                raise AssertionError("bare PDF unexpectedly passed pdfuaid:part")
            if bare_pdfua["MarkInfo/Marked"].passed:
                raise AssertionError("bare PDF unexpectedly passed MarkInfo/Marked")

            bare_pdfa = verify_pdf.check_pdfa(bare_path)
            if all(result.passed for result in bare_pdfa):
                raise AssertionError("bare PDF unexpectedly passed PDF/A identification")
    except Exception as e:
        failures.append(f"PDF conformance signals: {e}")

    checks += 1
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_dir = tmp_path / "input"
            out_dir = tmp_path / "output"
            input_dir.mkdir()
            (input_dir / "bravo.md").write_text("# Bravo\n", encoding="utf-8")
            (input_dir / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
            (input_dir / "ignored.txt").write_text("ignored\n", encoding="utf-8")

            jobs = make_pdf.plan_batch(input_dir, out_dir)
            expected = [
                (
                    input_dir / "alpha.md",
                    out_dir / "alpha.pdf",
                    out_dir / "alpha.html",
                ),
                (
                    input_dir / "bravo.md",
                    out_dir / "bravo.pdf",
                    out_dir / "bravo.html",
                ),
            ]
            if jobs != expected:
                raise AssertionError(f"unexpected batch plan: {jobs!r}")
    except Exception as e:
        failures.append(f"batch planning: {e}")

    checks += 1
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "in"
            input_dir.mkdir()
            (input_dir / "Report.md").write_text("# A\n", encoding="utf-8")
            (input_dir / "report.html").write_text("<html></html>", encoding="utf-8")
            try:
                make_pdf.plan_batch(input_dir, Path(tmpdir) / "out")
            except ValueError:
                pass
            else:
                raise AssertionError(
                    "case-insensitive output collision was not detected"
                )
    except Exception as e:
        failures.append(f"casefold collision guard: {e}")

    if failures:
        print(f"FAIL: {len(failures)} of {checks} checks failed")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print(f"PASS: {checks} offline make-pdf checks passed")


if __name__ == "__main__":
    main()
