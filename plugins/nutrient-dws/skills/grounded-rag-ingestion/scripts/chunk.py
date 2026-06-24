#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["nutrient-dws>=3.1.0", "pypdf>=4.0"]
# ///
"""Chunk a document into provenance-carrying JSONL via the Nutrient Data Extraction API.

This is a transformation layer on top of `document-extraction-api`'s `/extraction/parse`
(spatial output). It does NOT re-implement the API call: it reuses that skill's
`create_client()` + `client.parse(..., output_format="spatial")`, then normalizes the
typed elements, applies a chunking strategy, and emits one JSONL line per chunk. Each chunk
carries element type, page index, bounding box, confidence, and reading order — provenance a
downstream system can use to highlight the exact source region a retrieval result came from.

The script is embedding-agnostic: it stops at the chunk boundary. No vector DB, no embeddings.

Key: NUTRIENT_EXTRACT_API_KEY (DWS Extract is a separate product from DWS Processor). Falls back
to NUTRIENT_API_KEY only if the extract key is entirely unset (matching the extraction skill).

Usage:
  uv run scripts/chunk.py --input doc.pdf --out chunks.jsonl
  uv run scripts/chunk.py --input form.pdf --out - --mode understand --strategy table-row
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

# Per-page extraction-credit cost by mode (mirrors document-extraction-api).
MODE_COST = {"text": 1, "structure": 1.5, "understand": 9, "agentic": 18}
COST_GATE_CREDITS = 200

# Element types that only appear under understand/agentic mode. Used to warn when a low mode
# silently produces no key-value / formula chunks.
HIGH_MODE_ELEMENT_TYPES = ("keyValueRegion", "formula")


# --------------------------------------------------------------------------------------------
# Extraction-skill reuse: locate its scripts/ dir and import create_client (Decision 1).
# --------------------------------------------------------------------------------------------
def _extraction_scripts_dir() -> Path:
    """Resolve the document-extraction-api skill's scripts/ directory.

    Honors PARSE_SCRIPT_PATH when set; otherwise assumes the sibling-skill layout
    (../document-extraction-api/scripts relative to this file).
    """
    override = os.environ.get("PARSE_SCRIPT_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "document-extraction-api" / "scripts"


def _import_create_client():
    """Import create_client from the extraction skill, failing fast with a clear message."""
    scripts_dir = _extraction_scripts_dir()
    if not (scripts_dir / "lib" / "common.py").exists():
        raise RuntimeError(
            "document-extraction-api skill not found at expected path: "
            f"{scripts_dir}. Install the nutrient-dws plugin so both skills are siblings, "
            "or set PARSE_SCRIPT_PATH to the extraction skill's scripts/ directory."
        )
    sys.path.insert(0, str(scripts_dir))
    from lib.common import create_client  # noqa: E402

    return create_client


# --------------------------------------------------------------------------------------------
# Pure helpers (no network / SDK / key) — these carry the chunking contract and are unit-tested.
# --------------------------------------------------------------------------------------------
def compute_doc_id(input_path: Path, supplied: str | None) -> str:
    """Stable document identity: --doc-id if given, else a short content hash. Never basename."""
    if supplied:
        return supplied
    h = hashlib.sha256(input_path.read_bytes()).hexdigest()
    return h[:12]


def normalize_bbox(raw) -> dict:
    """Normalize bounds to {x, y, width, height} (OQ-1: object or [x1,y1,x2,y2] array)."""
    if isinstance(raw, dict):
        if "width" in raw and "height" in raw:
            return {
                "x": raw.get("x", 0),
                "y": raw.get("y", 0),
                "width": raw["width"],
                "height": raw["height"],
            }
        # {x1,y1,x2,y2} object form
        if {"x1", "y1", "x2", "y2"} <= set(raw):
            return {
                "x": raw["x1"],
                "y": raw["y1"],
                "width": raw["x2"] - raw["x1"],
                "height": raw["y2"] - raw["y1"],
            }
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        x1, y1, x2, y2 = raw
        return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
    return {"x": 0, "y": 0, "width": 0, "height": 0}


def union_bbox(a: dict, b: dict) -> dict:
    """Union of two normalized bboxes."""
    x1 = min(a["x"], b["x"])
    y1 = min(a["y"], b["y"])
    x2 = max(a["x"] + a["width"], b["x"] + b["width"])
    y2 = max(a["y"] + a["height"], b["y"] + b["height"])
    return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def _page_index(el: dict) -> int:
    page = el.get("page")
    if isinstance(page, dict):
        return page.get("pageIndex", 0)
    return el.get("pageIndex", 0)


def _reading_order(el: dict):
    return el.get("readingOrder")


def _element_text(el: dict) -> str:
    return el.get("text") or el.get("content") or ""


def _sort_key(el: dict):
    """Sort by (page_index, reading_order) with null reading_order last."""
    ro = _reading_order(el)
    return (_page_index(el), ro is None, ro if ro is not None else 0)


def _expand_grid(cells: list) -> list[list[str]]:
    """Expand table cells into a dense 2D grid, honoring rowSpan/colSpan so a merged cell appears
    in every row/column it covers. Raises on malformed cell geometry (caller falls back)."""
    max_row = max(c.get("row", 0) + max(c.get("rowSpan", 1), 1) - 1 for c in cells)
    max_col = max(c.get("column", 0) + max(c.get("colSpan", 1), 1) - 1 for c in cells)
    grid = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
    for c in cells:
        r0, c0 = c.get("row", 0), c.get("column", 0)
        text = c.get("text", "")
        for dr in range(max(c.get("rowSpan", 1), 1)):
            for dc in range(max(c.get("colSpan", 1), 1)):
                rr, cc = r0 + dr, c0 + dc
                if 0 <= rr <= max_row and 0 <= cc <= max_col and not grid[rr][cc]:
                    grid[rr][cc] = text
    return grid


def table_to_tsv(cells: list) -> tuple[str, bool]:
    """Render table cells (with row/col span expansion) into a TSV string.

    Returns (tsv_text, ok). ok=False signals an inconsistent grid the caller should flag with
    a chunking_warning rather than crash.
    """
    if not cells:
        return "", True
    try:
        grid = _expand_grid(cells)
        return "\n".join("\t".join(row) for row in grid), True
    except Exception:
        # Fall back to a flat join; caller emits a chunking_warning.
        return " ".join(c.get("text", "") for c in cells), False


def table_rows(cells: list) -> list[tuple[int, str]]:
    """Group cells into (row_index, row_tsv) tuples for --strategy table-row.

    Uses the same span expansion as table_to_tsv so a cell spanning multiple rows (a merged
    header or row label) appears in every row it covers — not only its top row, which would
    drop it from exactly the dense tables this strategy targets.
    """
    if not cells:
        return []
    try:
        grid = _expand_grid(cells)
        return [(r, "\t".join(grid[r])) for r in range(len(grid))]
    except Exception:
        # Fall back to naive per-row grouping (no span expansion) rather than crash.
        by_row: dict[int, list] = {}
        for c in cells:
            by_row.setdefault(c.get("row", 0), []).append(c)
        return [(row, "\t".join(c.get("text", "") for c in sorted(by_row[row],
                key=lambda c: c.get("column", 0)))) for row in sorted(by_row)]


def _pair_field(pair: dict, name: str) -> str:
    """Extract a key/value pair's text. Each side is a nested object with a `.value` string."""
    side = pair.get(name)
    if isinstance(side, dict):
        return side.get("value", "")
    return side if isinstance(side, str) else ""


def _pair_bbox(pair: dict) -> dict:
    k = pair.get("key")
    v = pair.get("value")
    kb = normalize_bbox(k.get("bounds")) if isinstance(k, dict) and k.get("bounds") else None
    vb = normalize_bbox(v.get("bounds")) if isinstance(v, dict) and v.get("bounds") else None
    if kb and vb:
        return union_bbox(kb, vb)
    return kb or vb or {"x": 0, "y": 0, "width": 0, "height": 0}


def _approx_tokens(text: str) -> int:
    return len(text.split())


def build_chunks(
    elements: list,
    doc_id: str,
    source_doc: str,
    strategy: str = "element",
    window_size: int = 512,
    skip_pictures: bool = False,
) -> list[dict]:
    """Transform sorted spatial elements into provenance chunks.

    chunk_id = {doc_id}__p{page}_r{reading_order}_e{element_index}{disc}
      - _e{element_index}: position in the (page, reading_order) sort -> inter-element
        uniqueness even when reading_order is null or shared (R16).
      - {disc}: intra-element discriminator (_tr / _kv / _w) for multi-chunk elements (R16).
    """
    ordered = sorted(elements, key=_sort_key)

    if strategy == "reading-order-window":
        return _build_windows(ordered, doc_id, source_doc, window_size)

    chunks: list[dict] = []
    for idx, el in enumerate(ordered):
        etype = el.get("type", "unknown")
        page = _page_index(el)
        ro = _reading_order(el)
        base = f"{doc_id}__p{page}_r{ro}_e{idx}"
        confidence = el.get("confidence")
        bbox = normalize_bbox(el.get("bounds") or el.get("bbox"))

        if etype == "table":
            cells = el.get("cells", [])
            if strategy == "table-row":
                for row_idx, row_text in table_rows(cells):
                    chunks.append(
                        _chunk(f"{base}_tr{row_idx}", doc_id, source_doc, "table_row",
                               page, ro, bbox, confidence, row_text)
                    )
            else:
                tsv, ok = table_to_tsv(cells)
                c = _chunk(base, doc_id, source_doc, "table", page, ro, bbox, confidence, tsv)
                if not ok:
                    c["chunking_warning"] = "table span-expansion inconsistent; emitted flat"
                chunks.append(c)

        elif etype == "keyValueRegion":
            for pi, pair in enumerate(el.get("pairs", [])):
                key_text = _pair_field(pair, "key")
                val_text = _pair_field(pair, "value")
                conf = pair.get("relationshipConfidence", confidence)
                chunks.append(
                    _chunk(f"{base}_kv{pi}", doc_id, source_doc, "key_value_pair",
                           page, ro, _pair_bbox(pair), conf, f"{key_text}: {val_text}")
                )

        elif etype == "formula":
            latex = el.get("latex", "")
            chunks.append(
                _chunk(base, doc_id, source_doc, "formula", page, ro, bbox, confidence,
                       f"[formula] {latex}")
            )

        elif etype == "picture":
            alt = el.get("altDescription") or ""
            if skip_pictures or not alt:
                continue
            chunks.append(
                _chunk(base, doc_id, source_doc, "picture", page, ro, bbox, confidence, alt)
            )

        else:  # paragraph, handwriting, and any other single-text element
            chunks.append(
                _chunk(base, doc_id, source_doc, etype, page, ro, bbox, confidence,
                       _element_text(el))
            )

    return chunks


def _build_windows(ordered: list, doc_id: str, source_doc: str, window_size: int) -> list[dict]:
    """Sliding window over reading-order-sorted text elements (paragraph/handwriting)."""
    text_els = [e for e in ordered if e.get("type") in ("paragraph", "handwriting")]
    chunks: list[dict] = []
    win: list[dict] = []
    tokens = 0
    win_idx = 0

    def flush(i: int):
        nonlocal win, tokens
        if not win:
            return
        text = " ".join(_element_text(e) for e in win)
        bbox = normalize_bbox(win[0].get("bounds") or win[0].get("bbox"))
        for e in win[1:]:
            bbox = union_bbox(bbox, normalize_bbox(e.get("bounds") or e.get("bbox")))
        page = _page_index(win[0])
        ro = _reading_order(win[0])
        confs = [e.get("confidence") for e in win if e.get("confidence") is not None]
        conf = min(confs) if confs else None
        chunks.append(
            _chunk(f"{doc_id}__p{page}_r{ro}_e{i}_w{win_idx}", doc_id, source_doc,
                   "reading_order_window", page, ro, bbox, conf, text)
        )
        win, tokens = [], 0

    for i, el in enumerate(text_els):
        # Never let a window straddle a page boundary: its chunk carries a single page_index and a
        # single bbox union, so mixing pages would mis-attribute provenance and point retrieval
        # highlights at the wrong page. Flush the in-progress window before crossing into a new page.
        if win and _page_index(el) != _page_index(win[0]):
            flush(i - 1)
            win_idx += 1
        win.append(el)
        tokens += _approx_tokens(_element_text(el))
        if tokens >= window_size:
            flush(i)
            win_idx += 1
    flush(len(text_els))
    return chunks


def _chunk(chunk_id, doc_id, source_doc, element_type, page, ro, bbox, confidence, text) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "source_doc": source_doc,
        "element_type": element_type,
        "page_index": page,
        "reading_order": ro,
        "bbox": bbox,
        "confidence": confidence,
        "text": text,
    }


def apply_min_confidence(chunks: list[dict], threshold: float) -> tuple[list[dict], int]:
    """Drop chunks below threshold. Returns (kept, dropped_count). Null confidence is kept."""
    if threshold <= 0:
        return chunks, 0
    kept = [c for c in chunks if c.get("confidence") is None or c["confidence"] >= threshold]
    return kept, len(chunks) - len(kept)


def preflight_decision(pages, mode: str, remaining, yes: bool, interactive: bool) -> tuple[bool, str]:
    """Decide whether the parse call may proceed before any network I/O (R10 / Decision 7).

    Returns (proceed, message). When pages is None (non-PDF), require --yes for high-cost modes.
    """
    cost_per_page = MODE_COST.get(mode, 1.5)
    if pages is None:
        if mode in ("understand", "agentic") and not yes:
            return False, (
                f"Cannot count pages locally for a non-PDF input; {mode} mode is "
                f"{cost_per_page} cr/page. Re-run with --yes to proceed."
            )
        return True, ""
    estimate = pages * cost_per_page
    limit = remaining if remaining is not None else COST_GATE_CREDITS
    if estimate > limit and not yes:
        msg = (
            f"Preflight: ~{estimate:g} extraction credits ({pages} page(s) x {cost_per_page} "
            f"cr/page at {mode} mode) exceeds the {limit:g}-credit gate. "
            "Re-run with --yes to proceed."
        )
        if interactive:
            answer = input(f"{msg}\nProceed anyway? [y/N] ").strip().lower()
            return answer in ("y", "yes"), msg
        return False, msg
    return True, ""


def _local_page_count(input_path: Path):
    """Best-effort local page count for the cost gate; None when not a countable PDF."""
    if input_path.suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(input_path)).pages)
    except Exception:
        return None


def mode_warns_empty(mode: str, elements: list) -> bool:
    """True if the response lacks high-mode element types because the mode was too low."""
    if mode in ("understand", "agentic"):
        return False
    return not any(e.get("type") in HIGH_MODE_ELEMENT_TYPES for e in elements)


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Chunk a document into provenance-carrying JSONL via the Nutrient Data Extraction "
            "API (spatial output). Embedding-agnostic: stops at the chunk boundary."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", required=True, help="Local input document path.")
    p.add_argument("--out", required=True, help="Output JSONL path, or '-' for stdout.")
    p.add_argument("--doc-id", dest="doc_id", default=None,
                   help="Stable document identity for chunk_id. Default: content hash of input.")
    p.add_argument("--mode", choices=["structure", "understand", "agentic"],
                   default="structure",
                   help="Parse mode. 'text' is intentionally not offered: this skill needs spatial "
                        "provenance and the API rejects text+spatial. keyValueRegion/formula "
                        "require understand+. Default: structure.")
    p.add_argument("--strategy", choices=["element", "reading-order-window", "table-row"],
                   default="element", help="Chunking strategy. Default: element.")
    p.add_argument("--window-size", dest="window_size", type=int, default=512,
                   help="Window size in tokens for reading-order-window strategy.")
    p.add_argument("--min-confidence", dest="min_confidence", type=float, default=0.0,
                   help="Drop chunks below this confidence (0-1). Null confidence is kept.")
    p.add_argument("--skip-pictures", dest="skip_pictures", action="store_true",
                   help="Omit picture chunks.")
    p.add_argument("--yes", action="store_true", help="Bypass the preflight cost gate.")
    return p


def _check_key_present() -> None:
    """Fail fast (R12) when no usable key is set, without importing the SDK. An empty string
    counts as unset (it would otherwise send an empty bearer token), mirroring the sibling skills."""
    if not (os.environ.get("NUTRIENT_EXTRACT_API_KEY") or os.environ.get("NUTRIENT_API_KEY")):
        print(
            "NUTRIENT_EXTRACT_API_KEY is not set. DWS Extract requires its own API key "
            "(separate from the DWS Processor key). Export it before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)


async def main() -> None:
    args = build_parser().parse_args()

    # 1. Key check (R12) — before any SDK import so the error path is clean.
    _check_key_present()

    # 2. Local-file validation (R13).
    raw = str(args.input).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        print("--input must be a local file path; download remote files first.", file=sys.stderr)
        sys.exit(1)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 3. Preflight cost gate (R10 / Decision 7) — implemented here, not inherited from parse.py.
    pages = _local_page_count(input_path)
    proceed, message = preflight_decision(
        pages, args.mode, remaining=None, yes=args.yes, interactive=sys.stdin.isatty()
    )
    if not proceed:
        print(message, file=sys.stderr)
        sys.exit(2)

    # 3b. Preflight the output target before the billable parse call, so a bad --out path fails
    # before consuming extraction credits (mirrors viewer-session.py's --jwt-out preflight).
    if args.out != "-":
        out_path = Path(args.out)
        out_parent = out_path.parent
        try:
            out_parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error: cannot create output directory {out_parent}: {e}", file=sys.stderr)
            sys.exit(1)
        if not os.access(out_parent, os.W_OK):
            print(f"Error: output directory is not writable: {out_parent}", file=sys.stderr)
            sys.exit(1)
        if out_path.is_symlink():
            print(f"Error: --out is a symlink; refusing to follow it: {args.out}", file=sys.stderr)
            sys.exit(1)
        if out_path.is_dir():
            print(f"Error: --out is a directory, not a file: {args.out}", file=sys.stderr)
            sys.exit(1)

    # 4. Parse (reuses the extraction skill's create_client + client.parse).
    create_client = _import_create_client()
    client = create_client()
    response = await client.parse(input_path, mode=args.mode, output_format="spatial")

    # Credit usage to stderr (R14) — numeric cost only, never the key.
    usage = response.get("usage", {}).get("data_extraction_credits", {})
    cost = usage.get("cost")
    if cost is not None:
        print(f"Usage: {cost} extraction credits ({args.mode} mode)", file=sys.stderr)

    elements = response.get("output", {}).get("elements", [])

    # Mode-gating warning (R7 / P2): KV & formula need understand+.
    if mode_warns_empty(args.mode, elements):
        print(
            f"Warning: keyValueRegion/formula elements are not populated under '{args.mode}' "
            "mode; key-value and formula chunks will be absent. Use --mode understand.",
            file=sys.stderr,
        )

    doc_id = compute_doc_id(input_path, args.doc_id)
    chunks = build_chunks(
        elements, doc_id, input_path.name, strategy=args.strategy,
        window_size=args.window_size, skip_pictures=args.skip_pictures,
    )
    chunks, dropped = apply_min_confidence(chunks, args.min_confidence)
    if dropped:
        print(f"Dropped {dropped} chunk(s) below --min-confidence {args.min_confidence}",
              file=sys.stderr)

    # 5. Serialize JSONL (stdout if --out '-', else a 0600 file).
    lines = "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks)
    if args.out == "-":
        sys.stdout.write(lines + ("\n" if lines else ""))
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Create atomically at 0600, refusing a symlinked target (O_NOFOLLOW) so the extracted
        # document text never lands at a wider, umask-derived mode and a pre-planted symlink can't
        # redirect it. fchmod enforces 0600 even when the file pre-existed at a wider mode.
        data = lines + ("\n" if lines else "")
        fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(data)
        print(f"Wrote {len(chunks)} chunk(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:  # noqa: BLE001
        print(str(e), file=sys.stderr)
        sys.exit(1)
