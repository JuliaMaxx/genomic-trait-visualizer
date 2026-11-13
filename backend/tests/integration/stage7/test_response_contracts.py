"""Published content, public response shapes and the existing TS generation path."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from backend import export_openapi
from backend.main import app
from backend.models.published_catalog import PublishedTrait
from backend.services.trait_curation.compiler import sha256

from .conftest import ROOT, SUPPORTED_ID

LEGACY_FIELDS = {"confidence", "confidence_percentage", "likelihood", "score", "weight"}


def assert_no_legacy_prediction(value: Any) -> None:
    if isinstance(value, dict):
        assert not LEGACY_FIELDS.intersection(value), "Legacy scoring in the API"
        for child in value.values():
            assert_no_legacy_prediction(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_legacy_prediction(child)
    elif isinstance(value, str):
        assert value not in {"likely", "unlikely", "inconclusive"}


def test_responses_preserve_published_content_traceability_and_release_identity(
    client: Any,
    dna_text: str,
    supported_release: Path,
    supported_trait: PublishedTrait,
) -> None:
    detail_response = client.get(f"/traits/{SUPPORTED_ID}")
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    published = supported_trait.model_dump(mode="json")
    for key, value in published.items():
        assert detail[key] == value, f"Published {key} must be returned unchanged"
    expected_identity = {
        "release_id": "synthetic-stage7-v1",
        "manifest_sha256": sha256((supported_release / "manifest.json").read_bytes()),
        "release_set_id": detail["release_set_id"],
    }
    assert isinstance(expected_identity["release_set_id"], str)
    assert expected_identity["release_set_id"]
    response = client.post(
        "/analyze/", files={"file": ("fictional.txt", dna_text.encode(), "text/plain")}
    )
    assert response.status_code == 200, response.text
    summary = next(
        (item for item in response.json() if item["trait_id"] == SUPPORTED_ID), None
    )
    assert summary is not None, "Analysis did not use the selected release"
    assert summary["name"] == supported_trait.name
    assert summary["strategy"] == supported_trait.interpretation.strategy
    for key in ("sources", "claims"):
        assert summary[key] == published[key]
    assert summary["claims"][0]["limitations"] == published["claims"][0]["limitations"]
    # Explanation -> claim -> evidence -> original source remains resolvable.
    claims = {item["claim_id"]: item for item in detail["claims"]}
    evidence = {item["evidence_id"]: item for item in detail["evidence"]}
    sources = {item["source_id"] for item in detail["sources"]}
    for text in summary["explanations"]:
        assert text in published["explanations"]
        for claim_id in text["claim_ids"]:
            for evidence_id in claims[claim_id]["evidence_ids"]:
                assert set(evidence[evidence_id]["source_ids"]) <= sources
    evaluated = client.post(
        f"/traits/{SUPPORTED_ID}/evaluate",
        files={"file": ("fictional.txt", dna_text.encode(), "text/plain")},
    )
    assert evaluated.status_code == 200, evaluated.text
    catalog = client.get("/traits/")
    assert catalog.status_code == 200
    for payload in (detail, summary, evaluated.json()["trait"]):
        assert {key: payload[key] for key in expected_identity} == expected_identity
    for payload in (catalog.json(), detail, response.json(), evaluated.json()):
        assert_no_legacy_prediction(payload)


def test_openapi_describes_stage7_results_and_unsupported_upload_errors() -> None:
    schema = app.openapi()

    def resolve(node: dict[str, Any]) -> dict[str, Any]:
        while "$ref" in node:
            node = schema["components"]["schemas"][node["$ref"].rsplit("/", 1)[1]]
        return node

    def response_shape(path: str, method: str) -> dict[str, Any]:
        return resolve(
            schema["paths"][path][method]["responses"]["200"]["content"][
                "application/json"
            ]["schema"]
        )

    identity = {"release_id", "manifest_sha256", "release_set_id"}
    catalog_list = response_shape("/traits/", "get")
    assert catalog_list["type"] == "array"
    catalog_item = resolve(catalog_list["items"])
    catalog_fields = {"id", "name", "strategy"} | identity
    assert catalog_fields <= set(
        catalog_item["required"]
    ), "OpenAPI still exposes the legacy catalog contract"
    bulk = response_shape("/analyze/", "post")
    assert bulk["type"] == "array"
    summary = resolve(bulk["items"])
    assert {
        "trait_id",
        "name",
        "strategy",
        "status",
        "observation_status",
        "explanations",
        "sources",
        "claims",
    } | identity <= set(summary["required"])
    properties = summary["properties"]
    assert not LEGACY_FIELDS.intersection(properties)
    assert set(resolve(properties["strategy"])["enum"]) == {
        "allele_count",
        "educational",
    }
    assert set(resolve(properties["status"])["enum"]) == {
        "evaluated",
        "unavailable",
        "educational",
    }
    assert {"copies", "reason"} <= set(properties)
    detail = response_shape("/traits/{trait_id}", "get")
    detail_fields = {
        "id",
        "name",
        "interpretation",
        "explanations",
        "sources",
        "claims",
    } | identity
    assert detail_fields <= set(detail["required"])
    claim = resolve(resolve(detail["properties"]["claims"])["items"])
    assert "limitations" in claim["required"]
    evaluation = response_shape("/traits/{trait_id}/evaluate", "post")
    assert set(evaluation["required"]) == {"trait", "analysis"}
    result = resolve(evaluation["properties"]["analysis"])
    assert {"status", "copies", "reason", "explanations", "observation_status"} <= set(
        result["properties"]
    )
    assert not LEGACY_FIELDS.intersection(result["properties"])
    for route in ("/analyze/", "/traits/{trait_id}/evaluate"):
        assert "415" in schema["paths"][route]["post"]["responses"]


def test_existing_openapi_to_typescript_generation_preserves_stage7_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node = shutil.which("node")
    generator = ROOT / "frontend/node_modules/openapi-typescript/bin/cli.js"
    if node is None or not generator.is_file():
        pytest.skip("Type generation needs Node and frontend npm ci (existing tools)")
    assert node is not None
    exported = tmp_path / "openapi.json"
    generated = tmp_path / "generated-api.ts"
    monkeypatch.setattr(export_openapi, "OPENAPI_PATH", exported)
    # main() only prints a repository-relative path; keep its temporary output
    # root local to this test as well. No checked-in frontend file is written.
    monkeypatch.setattr(export_openapi, "PROJECT_ROOT", tmp_path)
    export_openapi.main()
    assert json.loads(exported.read_bytes()) == app.openapi()
    process = subprocess.run(
        [node, str(generator), str(exported), "-o", str(generated)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    types = generated.read_text(encoding="utf-8")
    for field in (
        "release_set_id",
        "release_id",
        "manifest_sha256",
        "observation_status",
        "copies",
        "reason",
        "limitations",
    ):
        assert field in types, f"Generated API types do not expose {field}"
    # Preserve the repository's checked-in contract convention, without running
    # api:generate/api:check (both overwrite frontend/openapi.json).
    assert json.loads((ROOT / "frontend/openapi.json").read_bytes()) == app.openapi()
    assert types == (ROOT / "frontend/src/types/generated-api.ts").read_text(
        encoding="utf-8"
    )
