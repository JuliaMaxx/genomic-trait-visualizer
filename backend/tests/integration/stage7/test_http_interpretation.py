"""Real multipart requests through existing routes, with no evaluator mocks."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from backend.main import app
from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import PublishedTrait, TraitCatalog
from backend.services.dna_service import ingest_dna, match_observation
from backend.services.trait_curation.offline import evaluate

from .conftest import SUPPORTED_ID

ROW = "rs12345678\t1\t101\tGA"
RESULT_FIELDS = ("status", "copies", "reason", "explanations")


def analyze(client: Any, text: str) -> list[dict[str, Any]]:
    response = client.post(
        "/analyze/", files={"file": ("fictional.txt", text.encode(), "text/plain")}
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert isinstance(items, list)
    assert {item["trait_id"] for item in items} == {
        "synthetic_allele",
        SUPPORTED_ID,
    }, "Analysis must use the selected published traits"
    return items


def test_supported_upload_uses_reviewed_allele_counts_on_both_analysis_routes(
    client: Any, dna_text: str, supported_trait: PublishedTrait
) -> None:
    assert isinstance(supported_trait.interpretation, AlleleCountInterpretation)
    for genotype, copies in (("GG", 0), ("GA", 1), ("AA", 2)):
        text = dna_text.replace(ROW, f"rs12345678\t1\t101\t{genotype}")
        match = match_observation(
            ingest_dna(text.splitlines()), supported_trait.interpretation.requirements
        )
        assert match.status == "usable"
        expected = evaluate(supported_trait, match.observation).model_dump(mode="json")
        # Explicit independent arithmetic prevents merely agreeing with an oracle
        # from hiding a regression in the shared offline evaluator.
        assert expected["status"] == "evaluated" and expected["copies"] == copies

        items = analyze(client, text)
        summary = next(item for item in items if item["trait_id"] == SUPPORTED_ID)
        response = client.post(
            f"/traits/{SUPPORTED_ID}/evaluate",
            files={"file": ("fictional.txt", text.encode(), "text/plain")},
        )
        assert response.status_code == 200, response.text
        detail = response.json()
        assert detail["trait"]["id"] == SUPPORTED_ID
        assert detail["trait"]["interpretation"]["strategy"] == "allele_count"
        assert summary["strategy"] == "allele_count"
        for result in (summary, detail["analysis"]):
            assert {key: result.get(key) for key in RESULT_FIELDS} == expected
            assert result["observation_status"] == "usable"
        for key in ("release_id", "manifest_sha256", "release_set_id"):
            assert summary[key] == detail["trait"][key]


def test_missing_marker_is_unavailable_with_reviewed_unavailable_explanation(
    client: Any, dna_text: str, supported_trait: PublishedTrait
) -> None:
    text = dna_text.replace(ROW + "\n", "")
    items = analyze(client, text)
    result = next(item for item in items if item["trait_id"] == SUPPORTED_ID)
    expected = evaluate(supported_trait, None).model_dump(mode="json")
    assert {key: result.get(key) for key in RESULT_FIELDS} == expected
    assert result["status"] == "unavailable" and result["copies"] is None
    assert result["reason"] == "missing_genotype"
    assert result["observation_status"] == "absent"
    assert {text["result_key"] for text in result["explanations"]} == {
        None,
        "unavailable",
    }


@pytest.mark.parametrize(
    "rows,observation_status",
    [
        ("rs12345678\t1\t101\t--", "no_call"),
        ("rs12345678\t1\t101\tAA?", "partial"),
        ("rs12345678\t1\t101\tZZ", "invalid"),
        (ROW + "\nrs12345678\t1\t101\tAA", "conflicting"),
        ("rs12345678\t1\t102\tGA", "incompatible"),
    ],
    ids=["no-call", "partial", "invalid", "conflicting", "wrong-locus"],
)
def test_unusable_observations_cannot_receive_a_normal_interpretation(
    client: Any,
    dna_text: str,
    supported_trait: PublishedTrait,
    rows: str,
    observation_status: str,
) -> None:
    text = dna_text.replace(ROW, rows)
    items = analyze(client, text)
    summary = next(item for item in items if item["trait_id"] == SUPPORTED_ID)
    response = client.post(
        f"/traits/{SUPPORTED_ID}/evaluate",
        files={"file": ("fictional.txt", text.encode(), "text/plain")},
    )
    assert response.status_code == 200, response.text
    expected = evaluate(supported_trait, None).model_dump(mode="json")
    for result in (summary, response.json()["analysis"]):
        assert {key: result.get(key) for key in RESULT_FIELDS} == expected
        assert result["observation_status"] == observation_status
        assert result["status"] == "unavailable" and result["copies"] is None


def test_an_incompatible_trait_does_not_withhold_a_different_compatible_trait(
    client: Any, dna_text: str
) -> None:
    # The retained release requires GRCh38; the other publication requires GRCh37.
    # The same uploaded marker is unsuitable for one and usable for the other.
    items = {item["trait_id"]: item for item in analyze(client, dna_text)}
    incompatible = items["synthetic_allele"]
    usable = items[SUPPORTED_ID]
    assert incompatible["status"] == "unavailable"
    assert incompatible["observation_status"] == "incompatible"
    assert incompatible["copies"] is None and incompatible["reason"]
    assert usable["status"] == "evaluated" and usable["copies"] == 1
    assert usable["release_set_id"] == incompatible["release_set_id"]


@pytest.mark.parametrize(
    "original,replacement,observation_status",
    [
        ("build 37", "build 38", "unsupported"),
        ("build 37", "reference version unspecified", "unresolved"),
        ("plus strand", "unknown strand", "unresolved"),
        ("plus strand", "minus strand", "incompatible"),
        (ROW, "rs12345678\t1\t101\tA", "unsupported"),
        (ROW, "rs12345678\t1\t101\tAA\u0085?", "invalid"),
    ],
)
def test_upload_preserves_representation_and_raw_call_problems(
    client: Any,
    dna_text: str,
    original: str,
    replacement: str,
    observation_status: str,
) -> None:
    assert original in dna_text
    text = dna_text.replace(original, replacement)
    for route in ("/analyze/", f"/traits/{SUPPORTED_ID}/evaluate"):
        response = client.post(
            route, files={"file": ("fictional.txt", text.encode(), "text/plain")}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        result = (
            next(item for item in payload if item["trait_id"] == SUPPORTED_ID)
            if isinstance(payload, list)
            else payload["analysis"]
        )
        assert result["status"] == "unavailable"
        assert result["copies"] is None and result["reason"] == "missing_genotype"
        assert result["observation_status"] == observation_status
        assert result["observation_diagnostics"]


def test_invalid_utf8_cannot_be_dropped_to_create_a_usable_call(
    client: Any, dna_text: str
) -> None:
    data = dna_text.encode().replace(ROW.encode(), b"rs12345678\t1\t101\tAA\xff")
    for route in ("/analyze/", f"/traits/{SUPPORTED_ID}/evaluate"):
        response = client.post(
            route, files={"file": ("fictional.txt", data, "text/plain")}
        )
        assert response.status_code == 415, response.text
        assert "unsupported" in response.json()["detail"].lower()


def test_unsupported_uploads_receive_an_explicit_http_error_on_both_routes(
    client: Any,
) -> None:
    vcf = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
        "1\t101\trs12345678\tG\tA\t.\tPASS\t.\tGT\t0/1\n"
    )
    for filename, text in (("sample.vcf", vcf), ("unknown.txt", "unsupported data\n")):
        for route in ("/analyze/", f"/traits/{SUPPORTED_ID}/evaluate"):
            response = client.post(
                route, files={"file": (filename, text.encode(), "text/plain")}
            )
            assert response.status_code == 415, response.text
            assert "unsupported" in response.json()["detail"].lower()


def test_educational_content_is_identical_with_and_without_a_relevant_genotype(
    supported_release: Path,
    educational_release: Path,
    select_releases: Callable[[list[Path]], Path],
    dna_text: str,
) -> None:
    from fastapi.testclient import TestClient

    trait = TraitCatalog.model_validate_json(
        (educational_release / "catalog.json").read_bytes()
    ).traits[0]
    select_releases([supported_release, educational_release])
    results = []
    with TestClient(app) as client:
        for text in (dna_text, dna_text.replace(ROW + "\n", "")):
            response = client.post(
                f"/traits/{trait.id}/evaluate",
                files={"file": ("fictional.txt", text.encode(), "text/plain")},
            )
            assert response.status_code == 200, response.text
            detail = response.json()
            assert detail["trait"]["interpretation"]["strategy"] == "educational"
            result = detail["analysis"]
            assert {key: result.get(key) for key in RESULT_FIELDS} == evaluate(
                trait, None
            ).model_dump(mode="json")
            assert result["status"] == "educational"
            assert result["copies"] is None and result["reason"] is None
            assert result["observation_status"] is None
            results.append(result)
            bulk = client.post(
                "/analyze/",
                files={"file": ("fictional.txt", text.encode(), "text/plain")},
            )
            assert bulk.status_code == 200, bulk.text
            summary = next(item for item in bulk.json() if item["trait_id"] == trait.id)
            assert summary["strategy"] == summary["status"] == "educational"
            assert summary["copies"] is None and summary["observation_status"] is None
            assert summary["explanations"] == result["explanations"]
    assert results[0] == results[1]
