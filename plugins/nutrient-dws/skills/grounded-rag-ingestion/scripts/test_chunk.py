#!/usr/bin/env python3
"""Unit + CLI error-path tests for chunk.py.

Pure-function tests need no API key, SDK, or network — they exercise the chunking contract
(provenance schema, chunk_id uniqueness incl. the _e inter-element discriminator, nested
key-value text, table-row, windows, min-confidence, span-expansion fallback, mode-gating).
CLI tests run the script as a subprocess via plain `python3` (error paths exit before any
third-party import) to confirm fail-fast behavior.

Run: `python3 test_chunk.py`  (or `python3 -m pytest test_chunk.py`)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import chunk as C  # noqa: E402

SCRIPT = Path(__file__).parent / "chunk.py"


# --- doc_id / R15 ---------------------------------------------------------------------------
def test_doc_id_supplied_wins():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(b"%PDF-1.4 stuff")
        f.flush()
        assert C.compute_doc_id(Path(f.name), "my-id") == "my-id"


def test_doc_id_content_hash_stable_and_distinct():
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.pdf", Path(d) / "b.pdf"
        a.write_bytes(b"alpha content")
        b.write_bytes(b"beta content")
        id_a1 = C.compute_doc_id(a, None)
        id_a2 = C.compute_doc_id(a, None)
        id_b = C.compute_doc_id(b, None)
        assert id_a1 == id_a2          # idempotent on identical bytes
        assert id_a1 != id_b           # distinct content -> distinct id
        assert a.name not in id_a1     # never the basename


# --- chunk_id inter-element uniqueness / R16 (the Round-4 _e fix) ----------------------------
def test_null_reading_order_chunks_are_distinct():
    els = [
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": None, "text": "one"},
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": None, "text": "two"},
    ]
    ids = [c["chunk_id"] for c in C.build_chunks(els, "doc", "f.pdf")]
    assert len(ids) == len(set(ids)) == 2, ids
    assert all("_e" in i for i in ids)


def test_shared_reading_order_chunks_are_distinct():
    els = [
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": 5, "text": "a"},
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": 5, "text": "b"},
    ]
    ids = [c["chunk_id"] for c in C.build_chunks(els, "doc", "f.pdf")]
    assert len(set(ids)) == 2, ids


# --- key-value nested text / R7, P3 ---------------------------------------------------------
def test_keyvalue_uses_nested_value_fields():
    els = [{
        "type": "keyValueRegion", "page": {"pageIndex": 0}, "readingOrder": 3, "confidence": 0.9,
        "pairs": [
            {"key": {"value": "Total"}, "value": {"value": "$4.2B"}, "relationshipConfidence": 0.8},
            {"key": {"value": "Date"}, "value": {"value": "2024"}},
        ],
    }]
    chunks = C.build_chunks(els, "doc", "f.pdf")
    assert [c["text"] for c in chunks] == ["Total: $4.2B", "Date: 2024"]
    assert all(c["element_type"] == "key_value_pair" for c in chunks)
    ids = [c["chunk_id"] for c in chunks]
    assert len(set(ids)) == 2 and ids[0].endswith("_kv0") and ids[1].endswith("_kv1")
    assert chunks[0]["confidence"] == 0.8           # relationshipConfidence wins
    assert chunks[1]["confidence"] == 0.9           # falls back to element confidence
    # No dict reprs leaked into text:
    assert "{" not in chunks[0]["text"]


# --- table strategies / R6 ------------------------------------------------------------------
def test_table_row_strategy_distinct_ids():
    els = [{
        "type": "table", "page": {"pageIndex": 0}, "readingOrder": 2,
        "cells": [
            {"row": 0, "column": 0, "text": "h1"}, {"row": 0, "column": 1, "text": "h2"},
            {"row": 1, "column": 0, "text": "a"}, {"row": 1, "column": 1, "text": "b"},
        ],
    }]
    chunks = C.build_chunks(els, "doc", "f.pdf", strategy="table-row")
    assert [c["element_type"] for c in chunks] == ["table_row", "table_row"]
    ids = [c["chunk_id"] for c in chunks]
    assert ids[0].endswith("_tr0") and ids[1].endswith("_tr1")
    assert len(set(ids)) == 2
    assert chunks[0]["text"] == "h1\th2"


def test_whole_table_default_is_single_chunk_with_tsv():
    els = [{
        "type": "table", "page": {"pageIndex": 0}, "readingOrder": 2,
        "cells": [{"row": 0, "column": 0, "text": "x"}, {"row": 1, "column": 0, "text": "y"}],
    }]
    chunks = C.build_chunks(els, "doc", "f.pdf")
    assert len(chunks) == 1 and chunks[0]["element_type"] == "table"
    assert "chunking_warning" not in chunks[0]


def test_span_expansion_does_not_crash():
    els = [{
        "type": "table", "page": {"pageIndex": 0}, "readingOrder": 2,
        "cells": [{"row": 0, "column": 0, "rowSpan": 2, "text": "merged"},
                  {"row": 0, "column": 1, "text": "b"}, {"row": 1, "column": 1, "text": "c"}],
    }]
    chunks = C.build_chunks(els, "doc", "f.pdf")
    assert "merged" in chunks[0]["text"]


def test_bad_grid_sets_chunking_warning():
    els = [{
        "type": "table", "page": {"pageIndex": 0}, "readingOrder": 2,
        "cells": [{"row": None, "column": 0, "text": "boom"}],  # None row -> expansion error
    }]
    chunks = C.build_chunks(els, "doc", "f.pdf")
    assert chunks[0].get("chunking_warning")


# --- reading-order windows ------------------------------------------------------------------
def test_window_strategy_distinct_ids():
    els = [
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": i,
         "text": "word " * 300} for i in range(3)
    ]
    chunks = C.build_chunks(els, "doc", "f.pdf", strategy="reading-order-window", window_size=512)
    assert len(chunks) >= 2
    ids = [c["chunk_id"] for c in chunks]
    assert len(set(ids)) == len(ids)
    assert all(c["element_type"] == "reading_order_window" for c in chunks)


def test_window_flushes_on_page_boundary():
    # Two short paragraphs on different pages must NOT merge into one window (provenance integrity),
    # even when the token budget is far from full.
    els = [
        {"type": "paragraph", "page": {"pageIndex": 0}, "readingOrder": 0, "text": "page one"},
        {"type": "paragraph", "page": {"pageIndex": 1}, "readingOrder": 0, "text": "page two"},
    ]
    chunks = C.build_chunks(els, "doc", "f.pdf", strategy="reading-order-window", window_size=10000)
    assert sorted(c["page_index"] for c in chunks) == [0, 1], "window merged across a page boundary"
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)


# --- min-confidence -------------------------------------------------------------------------
def test_min_confidence_filters_and_keeps_null():
    chunks = [
        {"confidence": 0.2}, {"confidence": 0.99}, {"confidence": None},
    ]
    kept, dropped = C.apply_min_confidence(chunks, 0.5)
    assert dropped == 1
    assert {0.99, None} == {c["confidence"] for c in kept}


# --- bbox normalization / OQ-1 --------------------------------------------------------------
def test_normalize_bbox_object_and_array():
    assert C.normalize_bbox({"x": 1, "y": 2, "width": 3, "height": 4}) == \
        {"x": 1, "y": 2, "width": 3, "height": 4}
    assert C.normalize_bbox([10, 20, 30, 50]) == {"x": 10, "y": 20, "width": 20, "height": 30}


# --- skip pictures --------------------------------------------------------------------------
def test_picture_without_alt_is_skipped():
    els = [{"type": "picture", "page": {"pageIndex": 0}, "readingOrder": 1, "altDescription": ""}]
    assert C.build_chunks(els, "doc", "f.pdf") == []


# --- preflight cost gate / R10 --------------------------------------------------------------
def test_preflight_gate_blocks_over_threshold():
    proceed, msg = C.preflight_decision(30, "understand", None, yes=False, interactive=False)
    assert proceed is False and "gate" in msg          # 30 * 9 = 270 > 200
    proceed2, _ = C.preflight_decision(30, "understand", None, yes=True, interactive=False)
    assert proceed2 is True
    proceed3, _ = C.preflight_decision(5, "structure", None, yes=False, interactive=False)
    assert proceed3 is True                              # 5 * 1.5 = 7.5 < 200


def test_preflight_non_pdf_requires_yes_for_high_mode():
    proceed, _ = C.preflight_decision(None, "agentic", None, yes=False, interactive=False)
    assert proceed is False
    proceed2, _ = C.preflight_decision(None, "agentic", None, yes=True, interactive=False)
    assert proceed2 is True
    proceed3, _ = C.preflight_decision(None, "structure", None, yes=False, interactive=False)
    assert proceed3 is True


# --- mode-gating warning / R7, P2 -----------------------------------------------------------
def test_mode_warns_empty():
    assert C.mode_warns_empty("structure", [{"type": "paragraph"}]) is True
    assert C.mode_warns_empty("understand", [{"type": "paragraph"}]) is False
    assert C.mode_warns_empty("structure", [{"type": "keyValueRegion"}]) is False


# --- CLI error paths (subprocess, plain python3, no deps needed) -----------------------------
def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("NUTRIENT_EXTRACT_API_KEY", None)
    env.pop("NUTRIENT_API_KEY", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=env)


def test_help_exits_zero():
    r = _run(["--help"])
    assert r.returncode == 0 and "chunk" in r.stdout.lower()


def test_missing_key_exits_nonzero():
    r = _run(["--input", "x.pdf", "--out", "-"])
    assert r.returncode != 0 and "NUTRIENT_EXTRACT_API_KEY" in r.stderr


def test_missing_file_exits_nonzero():
    r = _run(["--input", "/nope/missing.pdf", "--out", "-"], {"NUTRIENT_EXTRACT_API_KEY": "k"})
    assert r.returncode != 0 and "not found" in r.stderr


def test_remote_url_rejected():
    r = _run(["--input", "https://example.com/x.pdf", "--out", "-"],
             {"NUTRIENT_EXTRACT_API_KEY": "k"})
    assert r.returncode != 0 and "local file" in r.stderr


def test_table_rows_expands_rowspan():
    # A header cell spanning rows 0-1 must appear in BOTH row chunks, not just row 0.
    cells = [
        {"row": 0, "column": 0, "rowSpan": 2, "text": "Region"},
        {"row": 0, "column": 1, "text": "Q1"},
        {"row": 1, "column": 1, "text": "Q2"},
    ]
    rows = dict(C.table_rows(cells))
    assert "Region" in rows[0] and "Region" in rows[1], "row-spanning header dropped from row 1"
    assert "Q1" in rows[0] and "Q2" in rows[1]


def test_mode_text_rejected():
    # text mode can't produce spatial provenance (API rejects text+spatial); argparse refuses it.
    r = _run(["--input", "x.pdf", "--out", "-", "--mode", "text"], {"NUTRIENT_EXTRACT_API_KEY": "k"})
    assert r.returncode != 0 and "invalid choice: 'text'" in r.stderr


# --- plain runner ---------------------------------------------------------------------------
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
