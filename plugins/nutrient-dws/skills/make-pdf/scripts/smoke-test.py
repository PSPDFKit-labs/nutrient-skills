#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py[linkify,plugins]"]
# ///

import importlib.util
import re
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).with_name("make-pdf.py")


def import_make_pdf():
    spec = importlib.util.spec_from_file_location("make_pdf", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_pdf"] = module
    spec.loader.exec_module(module)
    return module


def assert_contains(value: str, needle: str, label: str) -> None:
    if needle not in value:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    make_pdf = import_make_pdf()
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

    if failures:
        print(f"FAIL: {len(failures)} of {checks} checks failed")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print(f"PASS: {checks} offline make-pdf checks passed")


if __name__ == "__main__":
    main()
