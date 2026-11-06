"""Historical software regressions only; no assertion is scientific ground truth."""

import hashlib
import inspect
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "data" / "legacy" / "3ffbaf3"
MANIFEST = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))
HISTORICAL = json.loads(
    (BASELINE / MANIFEST["historical_outputs"]["path"]).read_text(encoding="utf-8")
)


def test_archived_catalog_and_environment_have_recorded_identities() -> None:
    catalog = MANIFEST["catalog"]
    archived = (BASELINE / catalog["archive_path"]).read_bytes()
    assert hashlib.sha256(archived).hexdigest() == catalog["sha256"]
    assert json.loads(archived)["version"] == catalog["schema_version"]
    environment = MANIFEST["environment"]
    assert (
        hashlib.sha256(
            (BASELINE / environment["dependency_snapshot"]).read_bytes()
        ).hexdigest()
        == environment["dependency_snapshot_sha256"]
    )


def test_historical_snapshot_has_recorded_identity() -> None:
    outputs = MANIFEST["historical_outputs"]
    assert (
        hashlib.sha256((BASELINE / outputs["path"]).read_bytes()).hexdigest()
        == outputs["sha256"]
    )
    assert len(HISTORICAL["cases"]) == outputs["case_count"] == 32
    assert len({case["case_id"] for case in HISTORICAL["cases"]}) == 32
    assert (
        MANIFEST["scientific_status"]
        == "scientifically_superseded_not_independently_validated"
    )


def _git(*args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssertionError(
            f"Historical replay Git verification failed: {exc}"
        ) from exc
    return completed.stdout


@pytest.fixture(scope="module")
def legacy_checkout() -> None:
    if os.environ.get("WHOAMI_LEGACY_REPLAY") != "1":
        pytest.skip(
            "Set WHOAMI_LEGACY_REPLAY=1 in the original checkout to replay history."
        )

    commit = MANIFEST["engine_commit"]
    assert Path(_git("rev-parse", "--show-toplevel").decode().strip()).resolve() == ROOT
    assert (
        _git("rev-parse", "HEAD").decode().strip() == commit
    ), f"Historical replay requires original checkout {commit}."
    # Archived additions and this replay harness are allowed; original backend
    # files must match the recorded commit, including staged changes.
    _git(
        "diff",
        "--exit-code",
        commit,
        "--",
        "backend",
        ":(exclude)backend/tests/unit/test_legacy_baseline.py",
    )
    original = _git("show", f"{commit}:data/traits.json").replace(b"\r\n", b"\n")
    archived = (BASELINE / MANIFEST["catalog"]["archive_path"]).read_bytes()
    assert archived.replace(b"\r\n", b"\n") == original
    assert (ROOT / "data" / "traits.json").read_bytes().replace(
        b"\r\n", b"\n"
    ) == original


@pytest.mark.parametrize("case", HISTORICAL["cases"], ids=lambda case: case["case_id"])
@pytest.mark.usefixtures("legacy_checkout")
def test_historical_service_output(case: dict) -> None:
    # Import only after provenance checks, so normal development tests do not
    # depend on the legacy models or evaluator still existing.
    from backend.models import Variant
    from backend.services.trait_service import calculate_single_trait

    assert (
        Path(inspect.getfile(Variant)).resolve() == ROOT / "backend/models/analysis.py"
    )
    assert (
        Path(inspect.getfile(calculate_single_trait)).resolve()
        == ROOT / "backend/services/trait_service.py"
    )

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
