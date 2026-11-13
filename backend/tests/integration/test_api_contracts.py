"""HTTP contract checks against an explicitly selected fictional publication."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    selection = tmp_path / "active.json"
    selection.write_text(
        json.dumps(
            {"releases": [str(ROOT / "data/releases/synthetic-stage4-demo-v1")]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WHOAMI_ACTIVE_RELEASE_SET", str(selection))
    with TestClient(app) as active_client:
        yield active_client


def test_openapi_contains_only_public_request_and_response_models() -> None:
    schema = app.openapi()
    models = schema["components"]["schemas"]

    assert "/traits/{trait_id}" in schema["paths"]
    assert "/traits/{trait_id}/detail" not in schema["paths"]
    assert "TraitAnalysisDetail" in models
    assert "TraitCatalogDetail" in models
    assert "TraitEvaluation" not in models
    assert "ParseResult" not in models


def test_catalog_and_rsid_routes_return_their_declared_models(
    client: TestClient,
) -> None:
    listing = client.get("/traits/")
    detail = client.get("/traits/synthetic_allele")
    assert listing.status_code == detail.status_code == 200
    trait = detail.json()
    assert [item["id"] for item in listing.json()] == ["synthetic_allele"]
    assert trait["interpretation"]["strategy"] == "allele_count"
    assert trait["sources"] and trait["claims"] and trait["explanations"]
    assert "analysis" not in trait
    # Browsing is explicitly withheld rather than reading the legacy catalog.
    markers = client.get("/rsids/")
    assert markers.status_code == 200 and markers.json() == []
    assert client.get("/rsids/rs4988235").status_code == 404


def test_analysis_routes_serialize_nested_catalog_and_user_data(
    client: TestClient,
) -> None:
    dna = (ROOT / "backend/tests/dna_samples/stage6/23andme_build37.txt").read_bytes()
    files = {"file": ("fictional.txt", dna, "text/plain")}
    summary = client.post("/analyze/", files=files)
    detail = client.post("/traits/synthetic_allele/evaluate", files=files)
    assert summary.status_code == detail.status_code == 200
    encoded_detail = detail.json()
    assert set(encoded_detail) == {"trait", "analysis"}
    assert encoded_detail["trait"]["id"] == "synthetic_allele"
    analysis = encoded_detail["analysis"]
    # This saved release requires GRCh38, while Stage 6 supports Build 37 uploads.
    assert analysis["status"] == "unavailable"
    assert analysis["copies"] is None
    assert analysis["observation_status"] == "incompatible"
    assert analysis["observation_diagnostics"]
    for key, value in analysis.items():
        assert summary.json()[0][key] == value


def test_search_route_returns_one_list_with_complete_results(
    client: TestClient,
) -> None:
    response = client.get("/search/", params={"q": "rs4988235"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "rs4988235"
    assert payload["results"] == []
