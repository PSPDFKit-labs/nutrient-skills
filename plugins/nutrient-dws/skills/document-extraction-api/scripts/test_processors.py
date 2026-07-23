#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "pytest>=8.0"]
# ///

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import extract as E
import processors as P


EXTRACT_SUCCESS = {
    "output": {"data": {"invoiceNumber": "INV-42"}, "metadata": {}},
    "usage": {"data_extraction_credits": {"cost": 15}},
}
PROCESSOR_CONFIG = {
    "schema": {
        "type": "object",
        "properties": {"invoiceNumber": {"type": "string"}},
    },
    "parseConfig": {"mode": "understand"},
    "options": {"includeCitations": True},
}


def test_extract_processor_url_sends_only_reference_version_and_store_run(
    tmp_path,
    monkeypatch,
):
    out_path = tmp_path / "result.json"
    key = "mock-extract-key"
    document_url = "https://example.test/invoice.pdf"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)

    def fake_post(url, **kwargs):
        assert url == E.EXTRACT_URL
        assert kwargs["headers"]["Authorization"] == f"Bearer {key}"
        assert kwargs["timeout"] == E.HTTP_TIMEOUT
        assert kwargs["json"] == {
            "url": document_url,
            "processor": "proc_invoice",
            "version": 3,
            "storeRun": True,
        }
        assert not {
            "schema",
            "parseConfig",
            "options",
        }.intersection(kwargs["json"])
        return httpx.Response(200, json=EXTRACT_SUCCESS)

    monkeypatch.setattr(E, "_post", fake_post)

    E.main(
        [
            "--url",
            document_url,
            "--processor",
            "proc_invoice",
            "--processor-version",
            "3",
            "--store-run",
            "--out",
            str(out_path),
        ]
    )

    assert json.loads(out_path.read_text(encoding="utf-8")) == EXTRACT_SUCCESS


def test_extract_rejects_processor_and_schema_together(
    tmp_path,
    monkeypatch,
    capsys,
):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(PROCESSOR_CONFIG["schema"]), encoding="utf-8")
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
                "--processor",
                "proc_invoice",
                "--schema",
                str(schema_path),
                "--out",
                str(tmp_path / "result.json"),
            ]
        )

    assert exc_info.value.code in {1, 2}
    assert (
        "--processor and --schema are mutually exclusive"
        in capsys.readouterr().err
    )


@pytest.mark.parametrize(
    ("argv", "expected_method", "expected_path", "expected_json"),
    [
        (
            ["list"],
            "GET",
            "/extraction/processors",
            None,
        ),
        (
            [
                "create",
                "--name",
                "Invoices",
                "--kind",
                "extract",
                "--config",
                "{config}",
                "--publish",
            ],
            "POST",
            "/extraction/processors",
            {
                "name": "Invoices",
                "kind": "extract",
                "config": PROCESSOR_CONFIG,
                "publish": True,
            },
        ),
        (
            ["show", "--processor", "proc_invoice"],
            "GET",
            "/extraction/processors/proc_invoice",
            None,
        ),
        (
            [
                "rename",
                "--processor",
                "proc_invoice",
                "--name",
                "Receipts",
            ],
            "PATCH",
            "/extraction/processors/proc_invoice",
            {"name": "Receipts"},
        ),
        (
            ["delete", "--processor", "proc_invoice"],
            "DELETE",
            "/extraction/processors/proc_invoice",
            None,
        ),
        (
            [
                "create-version",
                "--processor",
                "proc_invoice",
                "--config",
                "{config}",
            ],
            "POST",
            "/extraction/processors/proc_invoice/versions",
            {"config": PROCESSOR_CONFIG},
        ),
        (
            [
                "show-version",
                "--processor",
                "proc_invoice",
                "--version",
                "2",
            ],
            "GET",
            "/extraction/processors/proc_invoice/versions/2",
            None,
        ),
        (
            [
                "publish-version",
                "--processor",
                "proc_invoice",
                "--version",
                "2",
            ],
            "POST",
            "/extraction/processors/proc_invoice/versions/2/publish",
            None,
        ),
    ],
)
def test_processor_verb_uses_expected_method_path_and_body(
    tmp_path,
    monkeypatch,
    argv,
    expected_method,
    expected_path,
    expected_json,
):
    config_path = tmp_path / "processor-config.json"
    config_path.write_text(json.dumps(PROCESSOR_CONFIG), encoding="utf-8")
    argv = [
        str(config_path) if value == "{config}" else value
        for value in argv
    ]
    key = "mock-extract-key"
    monkeypatch.setattr(P, "resolve_extract_key", lambda: key)

    def fake_request(method, path, **kwargs):
        assert method == expected_method
        assert path == expected_path
        assert kwargs["headers"] == {"Authorization": f"Bearer {key}"}
        assert kwargs["timeout"] == P.HTTP_TIMEOUT
        if expected_json is None:
            assert "json" not in kwargs
        else:
            assert kwargs["json"] == expected_json
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(P, "_request", fake_request)

    P.main(argv)


def test_create_sends_name_kind_and_config_without_publish(
    tmp_path,
    monkeypatch,
):
    # The server requires both name and kind; publish is omitted when not set.
    config_path = tmp_path / "processor-config.json"
    config_path.write_text(json.dumps(PROCESSOR_CONFIG), encoding="utf-8")
    monkeypatch.setattr(P, "resolve_extract_key", lambda: "mock-key")

    def fake_request(_method, _path, **kwargs):
        assert kwargs["json"] == {
            "name": "Invoices",
            "kind": "extract",
            "config": PROCESSOR_CONFIG,
        }
        return httpx.Response(201, json={"publicId": "proc_invoice"})

    monkeypatch.setattr(P, "_request", fake_request)

    P.main(["create", "--name", "Invoices", "--kind", "extract", "--config", str(config_path)])


@pytest.mark.parametrize(
    "argv",
    [
        ["create", "--config", "c.json"],  # missing --name and --kind
        ["create", "--name", "Invoices", "--config", "c.json"],  # missing --kind
        ["create", "--kind", "extract", "--config", "c.json"],  # missing --name
    ],
)
def test_create_requires_name_and_kind(argv, monkeypatch):
    # argparse rejects the missing required options with exit code 2 before any network call.
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_a, **_k: pytest.fail("network must not be called"),
    )
    with pytest.raises(SystemExit) as exc_info:
        P.main(argv)
    assert exc_info.value.code == 2


def test_coded_processor_not_found_is_not_reported_as_feature_off(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(P, "resolve_extract_key", lambda: "mock-key")
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_args, **_kwargs: httpx.Response(
            404,
            json={
                "status": 404,
                "errorCode": "processor_not_found",
                "errorMessage": "Processor was not found.",
                "errorDetails": {"source": "processors", "code": "processor_not_found"},
            },
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        P.main(["show", "--processor", "proc_missing"])

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "processor_not_found" in stderr
    assert "Processor was not found." in stderr
    assert "feature may not be enabled" not in stderr


def test_coded_version_not_found_is_not_reported_as_feature_off(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(P, "resolve_extract_key", lambda: "mock-key")
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_args, **_kwargs: httpx.Response(
            404,
            json={
                "status": 404,
                "errorCode": "version_not_found",
                "errorMessage": "Version was not found.",
                "errorDetails": {"source": "processors", "code": "version_not_found"},
            },
        ),
    )

    with pytest.raises(SystemExit):
        P.main(
            [
                "show-version",
                "--processor",
                "proc_invoice",
                "--version",
                "99",
            ]
        )

    stderr = capsys.readouterr().err
    assert "version_not_found" in stderr
    assert "feature may not be enabled" not in stderr


@pytest.mark.parametrize("status_code", [403, 404])
def test_uncoded_forbidden_or_not_found_reports_feature_may_be_off(
    monkeypatch,
    capsys,
    status_code,
):
    monkeypatch.setattr(P, "resolve_extract_key", lambda: "mock-key")
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_args, **_kwargs: httpx.Response(
            status_code,
            json={"message": "Not available."},
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        P.main(["list"])

    assert exc_info.value.code == 1
    assert P.FEATURE_MAY_BE_OFF_MESSAGE in capsys.readouterr().err


def test_rename_collision_is_specific_and_not_reported_as_feature_off(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(P, "resolve_extract_key", lambda: "mock-key")
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_args, **_kwargs: httpx.Response(
            409,
            json={
                "status": 409,
                "errorCode": "name_taken",
                "errorMessage": "A processor with that name already exists.",
                "errorDetails": {"source": "processors", "code": "name_taken"},
            },
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        P.main(
            [
                "rename",
                "--processor",
                "proc_invoice",
                "--name",
                "Existing name",
            ]
        )

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "processor name collision" in stderr
    assert "already exists" in stderr
    assert "feature may not be enabled" not in stderr


def test_processor_http_error_redacts_key(monkeypatch, capsys):
    key = "mock-secret-key"
    monkeypatch.setattr(P, "resolve_extract_key", lambda: key)
    monkeypatch.setattr(
        P,
        "_request",
        lambda *_args, **_kwargs: httpx.Response(
            500,
            json={"message": f"upstream echoed {key}"},
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        P.main(["list"])

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "[REDACTED]" in stderr
    assert key not in stderr


def test_processor_transport_error_redacts_key(monkeypatch, capsys):
    key = "mock-secret-key"
    monkeypatch.setattr(P, "resolve_extract_key", lambda: key)

    def fail_request(*_args, **_kwargs):
        raise httpx.ConnectError(f"failed with bearer {key}")

    monkeypatch.setattr(P, "_request", fail_request)

    with pytest.raises(SystemExit) as exc_info:
        P.main(["list"])

    assert exc_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "[REDACTED]" in stderr
    assert key not in stderr


# --- review-fix regressions ---------------------------------------------------------------
def test_processor_2xx_success_output_redacts_key(monkeypatch, capsys):
    # P1 (impl review): the key must be redacted even from a 2xx success payload.
    key = "mock-secret-key"
    monkeypatch.setattr(P, "resolve_extract_key", lambda: key)
    monkeypatch.setattr(
        P, "_request",
        lambda *_a, **_k: httpx.Response(200, json={"echoed": f"body has {key}"}),
    )
    P.main(["list"])
    out = capsys.readouterr().out
    assert key not in out and "[REDACTED]" in out


def test_extract_processor_colon_syntax_splits_id_and_version(tmp_path, monkeypatch):
    # P2-1: --processor proc_id:VERSION must send {"processor": id, "version": VERSION}.
    out_path = tmp_path / "result.json"
    key = "mock-extract-key"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)

    def fake_post(url, **kwargs):
        assert kwargs["json"]["processor"] == "proc_invoice"
        assert kwargs["json"]["version"] == 3
        return httpx.Response(200, json=EXTRACT_SUCCESS)

    monkeypatch.setattr(E, "_post", fake_post)
    E.main(["--url", "https://example.test/x.pdf", "--processor", "proc_invoice:3",
            "--out", str(out_path)])


def test_extract_processor_colon_and_flag_version_conflict(tmp_path, monkeypatch, capsys):
    # P2-1: giving the version twice (colon + flag) is an error.
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "k")
    with pytest.raises(SystemExit) as exc:
        E.main(["--url", "https://example.test/x.pdf", "--processor", "proc_invoice:3",
                "--processor-version", "4", "--out", str(tmp_path / "o.json")])
    assert exc.value.code == 1
    assert "version once" in capsys.readouterr().err


@pytest.mark.parametrize("bad", [":3", "proc_x:", "proc:a:3"])
def test_extract_processor_malformed_colon_syntax_rejected(bad, tmp_path, monkeypatch, capsys):
    # PR-review P2: empty id, empty version, or a colon in the id must be rejected cleanly,
    # not crash later (":3" previously produced an empty id -> Path(None)).
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "k")
    with pytest.raises(SystemExit) as exc:
        E.main(["--url", "https://example.test/x.pdf", "--processor", bad,
                "--out", str(tmp_path / "o.json")])
    assert exc.value.code == 1
    assert "--processor must be" in capsys.readouterr().err


def test_coded_403_404_is_not_reported_as_feature_off(monkeypatch, capsys):
    # PR-review P2: a CODED 403/404 (e.g. access_denied) must keep its code, not be labeled
    # "feature may not be enabled" (only an UNCODED 403/404 is the feature-gate signal).
    key = "mock-secret-key"
    monkeypatch.setattr(P, "resolve_extract_key", lambda: key)
    monkeypatch.setattr(
        P, "_request",
        lambda *_a, **_k: httpx.Response(
            403,
            json={
                "status": 403,
                "errorCode": "access_denied",
                "errorMessage": "nope",
                "errorDetails": {"source": "processors", "code": "access_denied"},
            },
        ),
    )
    with pytest.raises(SystemExit) as exc:
        P.main(["list"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "access_denied" in err
    assert "feature may not be enabled" not in err


def test_extract_processor_error_hints_feature_off(tmp_path, monkeypatch, capsys):
    # P2-2: a --processor run that errors hints the feature may be off (server ignores the ref).
    key = "mock-extract-key"
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", key)
    monkeypatch.setattr(
        E, "_post",
        lambda *_a, **_k: httpx.Response(400, json={"message": "schema is required"}),
    )
    with pytest.raises(SystemExit) as exc:
        E.main(["--url", "https://example.test/x.pdf", "--processor", "proc_invoice",
                "--out", str(tmp_path / "o.json")])
    assert exc.value.code == 1
    assert "data_extraction_processors feature" in capsys.readouterr().err
