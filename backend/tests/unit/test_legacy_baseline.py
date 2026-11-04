"""Historical software regressions only; no assertion is scientific ground truth."""

import hashlib
import json
from pathlib import Path

import pytest

from backend.models import Variant
from backend.services.trait_service import calculate_single_trait

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "data" / "legacy" / "3ffbaf3"
MANIFEST = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))
HISTORICAL = json.loads(
    (BASELINE / "historical-regressions.json").read_text(encoding="utf-8")
)


def test_archived_catalog_and_environment_have_recorded_identities() -> None:
    catalog = MANIFEST["catalog"]
    archived = (BASELINE / catalog["archive_path"]).read_bytes()
    assert hashlib.sha256(archived).hexdigest() == catalog["sha256"]
    assert len(archived) == catalog["size_bytes"]
    assert (
        json.loads(archived)[catalog["schema_version_field"]]
        == catalog["schema_version"]
    )
    assert (
        hashlib.sha256(archived.replace(b"\r\n", b"\n")).hexdigest()
        == catalog["git_blob_sha256"]
    )
    # Git checkouts may use LF or CRLF; the archive itself retains exact bytes.
    assert (ROOT / catalog["original_path"]).read_bytes().replace(
        b"\r\n", b"\n"
    ) == archived.replace(b"\r\n", b"\n")
    environment = MANIFEST["environment"]
    assert (
        hashlib.sha256(
            (BASELINE / environment["dependency_snapshot"]).read_bytes()
        ).hexdigest()
        == environment["dependency_snapshot_sha256"]
    )
    outputs = MANIFEST["historical_outputs"]
    assert (
        hashlib.sha256((BASELINE / outputs["path"]).read_bytes()).hexdigest()
        == outputs["sha256"]
    )
    assert len(HISTORICAL["cases"]) == outputs["case_count"]
    assert outputs["scientific_ground_truth"] is False
    assert MANIFEST["scientific_approval"] is False


def test_legacy_runtime_sources_match_recorded_engine() -> None:
    for path, expected in MANIFEST["engine"]["runtime_sources_sha256_lf"].items():
        contents = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(contents).hexdigest() == expected, path


@pytest.mark.parametrize("case", HISTORICAL["cases"], ids=lambda case: case["case_id"])
def test_historical_service_output(case: dict) -> None:
    detail = calculate_single_trait(
        case["trait_id"], [Variant.model_validate(item) for item in case["variants"]]
    )
    assert detail is not None
    analysis = detail.analysis
    expected = case["expected"]
    assert analysis.result == expected["result"]
    assert analysis.result_content.headline == expected["headline"]
    for field in ("score", "coverage", "confidence"):
        value = expected[field]
        if value is None:
            assert getattr(analysis, field) is None
        else:
            # Accommodate libm rounding without changing the historical expectation.
            assert getattr(analysis, field) == pytest.approx(
                value, rel=1e-12, abs=1e-12
            )
    assert [
        {
            "rsid": rule.rsid,
            "status": rule.status,
            "user_genotype": rule.user_genotype,
            "interpretation_score": (
                rule.interpretation.score if rule.interpretation is not None else None
            ),
            "contribution": rule.contribution,
        }
        for rule in analysis.rules
    ] == expected["rules"]
