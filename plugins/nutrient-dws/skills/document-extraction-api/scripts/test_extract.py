#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pytest>=8.0", "pypdf>=4.0"]
# ///

import json
import os
import stat
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import extract as E


SUCCESS_RESPONSE = {
    "output": {
        "data": {"invoiceNumber": "INV-42", "total": 125.0},
        "metadata": {"invoiceNumber": {"citations": [{"page": 0}]}},
    },
    "usage": {
        "data_extraction_credits": {
            "cost": 15,
            "remainingCredits": 985,
        }
    },
}


def _write_schema(path: Path, schema=None) -> Path:
    schema = schema or {
        "type": "object",
        "properties": {"invoiceNumber": {"type": "string"}},
    }
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def _schema_with_serialized_size(size: int) -> dict:
    schema = {"type": "object", "description": ""}
    fixed_size = len(json.dumps(schema).encode("utf-8"))
    schema["description"] = "x" * (size - fixed_size)
    assert len(json.dumps(schema).encode("utf-8")) == size
    return schema


def _install_transport(monkeypatch, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(E, "_post", client.post)
    return client


def _multipart_parts(request: httpx.Request) -> dict:
    content_type = request.headers["Content-Type"]
    message = BytesParser(policy=policy.default).parsebytes(
        (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n\r\n"
        ).encode("ascii")
        + request.content
    )
    return {
        part.get_param("name", header="content-disposition"): part
        for part in message.iter_parts()
    }


def _run_cli(args, env_overrides=None):
    env = os.environ.copy()
    env.pop("NUTRIENT_EXTRACT_API_KEY", None)
    env.pop("NUTRIENT_API_KEY", None)
    env.update(env_overrides or {})
    return subprocess.run(
        [sys.executable, str(Path(E.__file__)), *map(str, args)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_load_and_validate_minimal_object_schema(tmp_path):
    schema_path = _write_schema(tmp_path / "schema.json", {"type": "object"})

    schema = E.load_schema(schema_path)
    E.validate_schema(schema, None)

    assert schema == {"type": "object"}


@pytest.mark.parametrize("schema", [[], {"type": "array"}, {"properties": {}}])
def test_validate_schema_rejects_non_object_root(schema):
    with pytest.raises(ValueError, match="root.*type 'object'"):
        E.validate_schema(schema, None)


def test_validate_schema_enforces_exact_32kb_boundary():
    E.validate_schema(_schema_with_serialized_size(E.MAX_SCHEMA_BYTES), None)

    with pytest.raises(ValueError, match="32768-byte"):
        E.validate_schema(
            _schema_with_serialized_size(E.MAX_SCHEMA_BYTES + 1),
            None,
        )


def test_validate_schema_enforces_instruction_boundary():
    E.validate_schema({"type": "object"}, "x" * E.MAX_INSTRUCTIONS)

    with pytest.raises(ValueError, match="10000-character"):
        E.validate_schema(
            {"type": "object"},
            "x" * (E.MAX_INSTRUCTIONS + 1),
        )


def test_validate_schema_accepts_deeply_nested_small_schema():
    nested = {"type": "string"}
    for level in range(12):
        nested = {
            "type": "object",
            "properties": {f"level{level}": nested},
        }

    E.validate_schema(nested, None)


def test_build_instructions_defaults_to_understand_and_citations():
    schema = {"type": "object"}
    args = E._build_parser().parse_args(
        ["--url", "https://example.test/doc.pdf", "--schema", "s", "--out", "o"]
    )

    result = E.build_instructions(
        schema,
        args.instructions,
        args.mode,
        not args.no_citations,
        args.store_run,
    )

    assert result == {
        "schema": schema,
        "parseConfig": {"mode": "understand"},
        "options": {"includeCitations": True},
    }


def test_build_instructions_supports_no_citations_and_store_run():
    result = E.build_instructions(
        {"type": "object"},
        "Extract the billed total.",
        "agentic",
        False,
        True,
    )

    assert result["options"] == {"includeCitations": False}
    assert result["instructions"] == "Extract the billed total."
    assert result["storeRun"] is True

    without_store = E.build_instructions(
        {"type": "object"},
        None,
        "understand",
        True,
        False,
    )
    assert "storeRun" not in without_store
    assert "instructions" not in without_store


def test_build_instructions_preserves_schema_key_order():
    schema = {
        "type": "object",
        "properties": {
            "zeta": {"type": "string"},
            "alpha": {"type": "number"},
        },
        "title": "Ordered",
    }

    result = E.build_instructions(schema, None, "understand", True, False)
    serialized = json.dumps(result, sort_keys=False)

    assert list(result["schema"]) == ["type", "properties", "title"]
    assert serialized.index('"zeta"') < serialized.index('"alpha"')


def test_estimate_cost_includes_extract_surcharge():
    assert E.estimate_cost(2, "understand") == 30.0
    assert E.estimate_cost(None, "understand") is None


def test_preflight_blocks_over_threshold_and_yes_proceeds():
    assert E.preflight(14, "understand", False) == (
        False,
        "Estimated extraction cost is 210 credits, above the 200-credit "
        "safety gate. Re-run with --yes to proceed.",
    )
    assert E.preflight(14, "understand", True) == (True, "")


def test_preflight_unknown_pages_warns_and_proceeds():
    ok, message = E.preflight(None, "understand", False)

    assert ok is True
    assert "cannot be pre-estimated" in message


def test_main_over_threshold_exits_two_before_network(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_path = tmp_path / "input.pdf"
    input_path.write_bytes(b"not needed because page count is mocked")
    schema_path = _write_schema(tmp_path / "schema.json")
    monkeypatch.setattr(E, "_local_page_count", lambda _path: 14)
    monkeypatch.setattr(
        E,
        "_post",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )

    with pytest.raises(SystemExit) as exc_info:
        E.main(
            [
                "--input",
                str(input_path),
                "--schema",
                str(schema_path),
                "--out",
                str(tmp_path / "out.json"),
            ]
        )

    assert exc_info.value.code == 2
    assert "210 credits" in capsys.readouterr().err


def test_summarize_response_reports_nested_metadata_honestly():
    response = {
        "output": {
            "data": {
                "customer": {"name": "Ada"},
                "items": [{"description": "Service"}],
            },
            "metadata": {
                "customer": {
                    "name": {"citations": [{"page": 0}]},
                }
            },
        }
    }

    summary = E.summarize_response(response)

    assert "customer, items" in summary
    assert "citations: present" in summary
    assert "uncited" not in summary


def test_summarize_response_reports_empty_metadata_as_no_citations():
    response = {
        "output": {
            "data": {"invoiceNumber": "INV-42"},
            "metadata": {},
        }
    }

    assert E.summarize_response(response).endswith("citations: none")


def test_local_request_wire_shape_safe_write_and_yes_proceeds(
    tmp_path,
    monkeypatch,
):
    input_path = tmp_path / "invoice.txt"
    input_path.write_bytes(b"invoice body")
    schema = {
        "type": "object",
        "properties": {
            "invoiceNumber": {"type": "string"},
            "total": {"type": "number"},
        },
    }
    schema_path = _write_schema(tmp_path / "schema.json", schema)
    out_path = tmp_path / "result.json"
    key = "mock-extract-key"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)
    monkeypatch.setattr(E, "_local_page_count", lambda _path: 14)

    def handler(request):
        assert str(request.url) == E.EXTRACT_URL
        assert request.headers["Authorization"] == f"Bearer {key}"
        parts = _multipart_parts(request)
        assert set(parts) == {"file", "instructions"}
        assert parts["file"].get_filename() == input_path.name
        assert parts["file"].get_payload(decode=True) == b"invoice body"
        assert parts["instructions"].get_filename() is None
        instructions = json.loads(
            parts["instructions"].get_payload(decode=True).decode("utf-8")
        )
        assert instructions == {
            "schema": schema,
            "parseConfig": {"mode": "understand"},
            "options": {"includeCitations": False},
        }
        return httpx.Response(200, json=SUCCESS_RESPONSE)

    client = _install_transport(monkeypatch, handler)
    try:
        E.main(
            [
                "--input",
                str(input_path),
                "--schema",
                str(schema_path),
                "--out",
                str(out_path),
                "--no-citations",
                "--yes",
            ]
        )
    finally:
        client.close()

    assert json.loads(out_path.read_text(encoding="utf-8")) == SUCCESS_RESPONSE
    assert stat.S_IMODE(out_path.stat().st_mode) == 0o600


def test_url_request_wire_shape_warns_and_proceeds(
    tmp_path,
    monkeypatch,
    capsys,
):
    schema = {
        "type": "object",
        "properties": {"invoiceNumber": {"type": "string"}},
    }
    schema_path = _write_schema(tmp_path / "schema.json", schema)
    out_path = tmp_path / "result.json"
    key = "mock-extract-key"
    document_url = "https://example.test/invoice.pdf"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)

    def handler(request):
        assert request.headers["Authorization"] == f"Bearer {key}"
        assert request.headers["Content-Type"].startswith("application/json")
        body = json.loads(request.content)
        assert body == {
            "url": document_url,
            "schema": schema,
            "parseConfig": {"mode": "understand"},
            "options": {"includeCitations": True},
            "instructions": "Extract the invoice number.",
            "storeRun": True,
        }
        assert "file" not in body
        return httpx.Response(200, json=SUCCESS_RESPONSE)

    client = _install_transport(monkeypatch, handler)
    try:
        E.main(
            [
                "--url",
                document_url,
                "--schema",
                str(schema_path),
                "--out",
                str(out_path),
                "--instructions",
                "Extract the invoice number.",
                "--store-run",
            ]
        )
    finally:
        client.close()

    captured = capsys.readouterr()
    assert "cannot be pre-estimated" in captured.err
    assert "citations: present" in captured.out
    assert out_path.exists()


def test_server_validation_error_is_surfaced_and_key_redacted(
    tmp_path,
    monkeypatch,
    capsys,
):
    schema_path = _write_schema(tmp_path / "schema.json")
    out_path = tmp_path / "result.json"
    key = "mock-secret-key"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)

    def handler(_request):
        return httpx.Response(
            422,
            text=(
                '{"error":"validation_error",'
                '"path":"schema.properties.deep","echo":"mock-secret-key"}'
            ),
        )

    client = _install_transport(monkeypatch, handler)
    try:
        with pytest.raises(SystemExit) as exc_info:
            E.main(
                [
                    "--url",
                    "https://example.test/invoice.pdf",
                    "--schema",
                    str(schema_path),
                    "--out",
                    str(out_path),
                ]
            )
    finally:
        client.close()

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "validation_error" in stderr
    assert "schema.properties.deep" in stderr
    assert "[REDACTED]" in stderr
    assert key not in stderr
    assert not out_path.exists()


@pytest.mark.parametrize(
    ("response_factory", "expected_error"),
    [
        (
            lambda key: httpx.Response(200, text=f"not-json {key}"),
            "was not valid JSON",
        ),
        (
            lambda key: httpx.Response(200, json={"message": f"no output {key}"}),
            "'output' object",
        ),
        (
            lambda key: httpx.Response(200, json={"output": None, "echo": key}),
            "'output' object",
        ),
    ],
)
def test_malformed_2xx_responses_fail_without_writing(
    tmp_path,
    monkeypatch,
    capsys,
    response_factory,
    expected_error,
):
    schema_path = _write_schema(tmp_path / "schema.json")
    out_path = tmp_path / "result.json"
    key = "mock-secret-key"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)
    client = _install_transport(
        monkeypatch,
        lambda _request: response_factory(key),
    )

    try:
        with pytest.raises(SystemExit) as exc_info:
            E.main(
                [
                    "--url",
                    "https://example.test/invoice.pdf",
                    "--schema",
                    str(schema_path),
                    "--out",
                    str(out_path),
                ]
            )
    finally:
        client.close()

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert expected_error in stderr
    assert "[REDACTED]" in stderr
    assert key not in stderr
    assert not out_path.exists()


@pytest.mark.parametrize(
    ("env_overrides", "expected_error"),
    [
        ({}, "NUTRIENT_EXTRACT_API_KEY is not set"),
        (
            {
                "NUTRIENT_EXTRACT_API_KEY": "",
                "NUTRIENT_API_KEY": "unused-fallback",
            },
            "NUTRIENT_EXTRACT_API_KEY is set but empty",
        ),
    ],
)
def test_cli_missing_or_empty_key_exits_one(
    tmp_path,
    env_overrides,
    expected_error,
):
    schema_path = _write_schema(tmp_path / "schema.json")

    result = _run_cli(
        [
            "--url",
            "https://example.test/invoice.pdf",
            "--schema",
            schema_path,
            "--out",
            tmp_path / "out.json",
        ],
        env_overrides,
    )

    assert result.returncode == 1
    assert expected_error in result.stderr


@pytest.mark.parametrize(
    "source_args",
    [
        [],
        [
            "--input",
            "unused.pdf",
            "--url",
            "https://example.test/invoice.pdf",
        ],
    ],
)
def test_cli_requires_exactly_one_input_or_url(tmp_path, source_args):
    schema_path = _write_schema(tmp_path / "schema.json")

    result = _run_cli(
        [
            *source_args,
            "--schema",
            schema_path,
            "--out",
            tmp_path / "out.json",
        ]
    )

    assert result.returncode == 1
    assert "exactly one of --input or --url" in result.stderr


def test_cli_rejects_processor_and_schema_together(tmp_path):
    schema_path = _write_schema(tmp_path / "schema.json")

    result = _run_cli(
        [
            "--url",
            "https://example.test/invoice.pdf",
            "--schema",
            schema_path,
            "--processor",
            "proc_invoice",
            "--out",
            tmp_path / "out.json",
        ]
    )

    assert result.returncode == 1
    assert "--processor and --schema are mutually exclusive" in result.stderr


def test_cli_missing_input_file_exits_one(tmp_path):
    schema_path = _write_schema(tmp_path / "schema.json")
    missing_path = tmp_path / "missing.pdf"

    result = _run_cli(
        [
            "--input",
            missing_path,
            "--schema",
            schema_path,
            "--out",
            tmp_path / "out.json",
        ]
    )

    assert result.returncode == 1
    assert f"input file not found: {missing_path}" in result.stderr


def test_symlink_output_is_refused_before_network(
    tmp_path,
    monkeypatch,
    capsys,
):
    schema_path = _write_schema(tmp_path / "schema.json")
    out_path = tmp_path / "result.json"
    out_path.symlink_to(tmp_path / "target.json")
    monkeypatch.setattr(
        E,
        "_post",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )

    with pytest.raises(SystemExit) as exc_info:
        E.main(
            [
                "--url",
                "https://example.test/invoice.pdf",
                "--schema",
                str(schema_path),
                "--out",
                str(out_path),
            ]
        )

    assert exc_info.value.code == 1
    assert "refusing to follow symlink" in capsys.readouterr().err


def test_directory_output_is_refused_before_network(
    tmp_path,
    monkeypatch,
    capsys,
):
    schema_path = _write_schema(tmp_path / "schema.json")
    out_path = tmp_path / "result"
    out_path.mkdir()
    monkeypatch.setattr(
        E,
        "_post",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )

    with pytest.raises(SystemExit) as exc_info:
        E.main(
            [
                "--url",
                "https://example.test/invoice.pdf",
                "--schema",
                str(schema_path),
                "--out",
                str(out_path),
            ]
        )

    assert exc_info.value.code == 1
    assert "must be a file, not a directory" in capsys.readouterr().err


# --- regression tests for adversarial-review fixes (implementation review) ------------------
def test_out_may_not_alias_input(tmp_path):
    # P1-2: --out == --input would be O_TRUNC'd after a paid call, destroying the source.
    same = tmp_path / "doc.pdf"
    same.write_bytes(b"%PDF-1.4 minimal")
    with pytest.raises(SystemExit) as exc:
        E._prepare_output(same, protected=[same])
    assert exc.value.code == 1


def test_schema_size_measured_as_utf8_not_ascii_escaped(tmp_path):
    # P1-3: a non-ASCII schema under 32 KB UTF-8 must pass even if its \uXXXX-escaped form
    # would exceed 32 KB. "€" is 3 UTF-8 bytes but 6 ASCII-escaped bytes.
    euros = "€" * 6000  # ~18 KB UTF-8, ~36 KB ascii-escaped
    schema = {"type": "object", "description": euros}
    assert len(json.dumps(schema, ensure_ascii=False).encode("utf-8")) < E.MAX_SCHEMA_BYTES
    assert len(json.dumps(schema).encode("utf-8")) > E.MAX_SCHEMA_BYTES  # would wrongly reject
    E.validate_schema(schema, None)  # must not raise


def test_load_schema_rejects_non_finite_constants(tmp_path):
    # P1-3: Python's json accepts NaN/Infinity; standard JSON does not.
    bad = tmp_path / "schema.json"
    bad.write_text('{"type": "object", "x": NaN}', encoding="utf-8")
    with pytest.raises(ValueError):
        E.load_schema(bad)


def test_yes_silences_unknown_page_warning():
    # P2-2: --yes silences the unknown-page note; without it, the note is emitted.
    ok, msg = E.preflight(None, "understand", yes=True)
    assert ok is True and msg == ""
    ok2, msg2 = E.preflight(None, "understand", yes=False)
    assert ok2 is True and "unknown" in msg2


def test_key_redacted_on_network_exception(tmp_path, monkeypatch, capsys):
    # P1-1: a transport error must not leak the bearer key to stderr.
    key = "supersecret-key-value"
    schema_path = _write_schema(tmp_path / "schema.json")
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4 minimal")
    out_path = tmp_path / "out.json"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)

    def boom(*_a, **_k):
        raise httpx.ConnectError(f"failed connecting with header Bearer {key}")

    monkeypatch.setattr(E, "_post", boom)
    with pytest.raises(SystemExit) as exc:
        E.main(["--input", str(doc), "--schema", str(schema_path),
                "--out", str(out_path), "--yes"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert key not in err and "[REDACTED]" in err


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
