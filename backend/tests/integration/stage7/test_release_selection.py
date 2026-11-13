"""Selection is explicit and verification happens during the real app lifespan."""

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from backend.main import app
from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import PublishedTrait
from backend.services.dna_service import ingest_dna, match_observation
from backend.services.trait_curation.compiler import sha256, stable_json, verify_release
from backend.services.trait_curation.offline import evaluate

from .conftest import EXAMPLES, ROOT, SELECTION_ENV, SUPPORTED_ID


def test_fictional_fixtures_are_separate_verified_publications(
    saved_release: Path,
    supported_release: Path,
    supported_trait: PublishedTrait,
    dna_text: str,
) -> None:
    manifests = [verify_release(path) for path in (saved_release, supported_release)]
    assert {item.trait_id for item in manifests} == {"synthetic_allele", SUPPORTED_ID}
    assert len({item.release_id for item in manifests}) == 2
    for path in (saved_release, supported_release):
        inputs = json.loads((path / "inputs.json").read_bytes())
        assert inputs["expected_cases"]["kind"] == "synthetic"
        assert inputs["decisions"]
        assert all(
            item["reviewer_id"].startswith("synthetic-") for item in inputs["decisions"]
        )
    assert isinstance(supported_trait.interpretation, AlleleCountInterpretation)
    match = match_observation(
        ingest_dna(dna_text.splitlines()), supported_trait.interpretation.requirements
    )
    assert match.status == "usable"
    assert evaluate(supported_trait, match.observation).copies == 1


def test_explicit_single_release_excludes_the_legacy_catalog(
    saved_release: Path,
    select_releases: Callable[[list[Path]], Path],
    dna_text: str,
) -> None:
    from fastapi.testclient import TestClient

    select_releases([saved_release])
    with TestClient(app) as client:
        response = client.get("/traits/")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [
            "synthetic_allele"
        ], "Only explicitly selected publications may be served"
        assert client.get("/traits/lactose_intolerance").status_code == 404
        unselected = client.post(
            "/traits/lactose_intolerance/evaluate",
            files={"file": ("fictional.txt", dna_text.encode(), "text/plain")},
        )
        assert unselected.status_code == 404


def test_search_and_rsid_routes_exclude_unselected_legacy_content(client: Any) -> None:
    # Empty lists are acceptable until search/marker browsing uses approved data.
    # Make every request before assertions so all three routes are exercised.
    searches = [
        client.get("/search/", params={"q": query})
        for query in ("", "lactose_intolerance", "rs4988235")
    ]
    markers = client.get("/rsids/")
    legacy_marker = client.get("/rsids/rs4988235")
    allowed_urls = {
        "/traits/synthetic_allele",
        f"/traits/{SUPPORTED_ID}",
        "/rsids/rs12345678",
    }
    for response in searches:
        assert response.status_code == 200, response.text
        urls = {item["url"] for item in response.json()["results"]}
        assert urls <= allowed_urls, "Search exposed an unselected legacy entry"
    assert markers.status_code == 200, markers.text
    marker_ids = {item["rsid"] for item in markers.json()}
    assert marker_ids <= {"rs12345678"}, "The marker catalog exposed legacy content"
    assert legacy_marker.status_code == 404, legacy_marker.text


def test_two_traits_share_release_set_identity_across_list_and_detail(
    client: Any,
    saved_release: Path,
    supported_release: Path,
    select_releases: Callable[[list[Path]], Path],
) -> None:
    response = client.get("/traits/")
    assert response.status_code == 200
    items = response.json()
    assert {item["id"] for item in items} == {"synthetic_allele", SUPPORTED_ID}
    identities = []
    for path in (saved_release, supported_release):
        manifest = verify_release(path)
        summary = next(item for item in items if item["id"] == manifest.trait_id)
        detail = client.get(f"/traits/{manifest.trait_id}")
        assert detail.status_code == 200
        for payload in (summary, detail.json()):
            assert payload["release_id"] == manifest.release_id
            assert payload["manifest_sha256"] == sha256(
                (path / "manifest.json").read_bytes()
            )
            identities.append(payload["release_set_id"])
    assert isinstance(identities[0], str) and identities[0]
    assert len(set(identities)) == 1
    # A running app keeps the verified startup snapshot until its next lifespan.
    select_releases([supported_release])
    assert client.get("/traits/").json() == items


def test_release_set_identity_survives_restart_reordering_and_relocation(
    saved_release: Path,
    supported_release: Path,
    second_version_release: Path,
    select_releases: Callable[[list[Path]], Path],
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    identities = []
    copied = tmp_path / "relocated"
    shutil.copytree(supported_release, copied)
    for paths in (
        [saved_release, supported_release],
        [copied, saved_release],
        [supported_release],
        [second_version_release, supported_release],
    ):
        select_releases(paths)
        with TestClient(app) as client:
            response = client.get(f"/traits/{SUPPORTED_ID}")
            assert response.status_code == 200
            assert response.json().get("release_set_id"), "Missing active set identity"
            identities.append(response.json()["release_set_id"])
    assert identities[0] == identities[1]
    assert identities[0] != identities[2], "Membership must affect the set identity"
    assert (
        identities[0] != identities[3]
    ), "Release versions must affect the set identity"


def test_startup_rejects_one_corrupted_member_of_an_otherwise_valid_set(
    saved_release: Path,
    supported_release: Path,
    select_releases: Callable[[list[Path]], Path],
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    damaged = tmp_path / "damaged"
    shutil.copytree(supported_release, damaged)
    catalog = damaged / "catalog.json"
    catalog.write_bytes(catalog.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity"):
        verify_release(damaged)
    select_releases([saved_release, damaged])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with TestClient(app):
            pytest.fail("Startup accepted a tampered active release")


def test_startup_rejects_invalid_approval_even_with_matching_file_checksums(
    supported_release: Path,
    select_releases: Callable[[list[Path]], Path],
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    damaged = tmp_path / "invalid-approval"
    shutil.copytree(supported_release, damaged)
    approval = json.loads((damaged / "approval.json").read_bytes())
    approval["manifest_sha256"] = "0" * 64
    (damaged / "approval.json").write_bytes(stable_json(approval))
    checksums = json.loads((damaged / "checksums.json").read_bytes())
    checksums["approval.json"] = sha256((damaged / "approval.json").read_bytes())
    (damaged / "checksums.json").write_bytes(stable_json(checksums))
    # Reach Stage 4's approval check, beyond a superficial checksum-only loader.
    with pytest.raises(ValueError, match="approval"):
        verify_release(damaged)
    select_releases([damaged])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with TestClient(app):
            pytest.fail("Startup accepted an invalid final release approval")


def test_duplicate_trait_ids_in_distinct_verified_releases_are_rejected(
    saved_release: Path,
    second_version_release: Path,
    select_releases: Callable[[list[Path]], Path],
) -> None:
    from fastapi.testclient import TestClient

    first = verify_release(saved_release)
    second = verify_release(second_version_release)
    assert first.release_id != second.release_id
    assert first.trait_id == second.trait_id
    select_releases([saved_release, second_version_release])
    with pytest.raises((ValueError, RuntimeError), match="(?i)duplicate.*trait"):
        with TestClient(app):
            pytest.fail("Startup accepted duplicate trait IDs")


@pytest.mark.parametrize("selection", ["unconfigured", "missing", "invalid", "empty"])
def test_absent_or_invalid_selection_cannot_start_the_legacy_app(
    selection: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    path = tmp_path / "selection.json"
    monkeypatch.delenv(SELECTION_ENV, raising=False)
    if selection != "unconfigured":
        monkeypatch.setenv(SELECTION_ENV, str(path))
    if selection == "invalid":
        path.write_text("{not valid JSON", encoding="utf-8")
    elif selection == "empty":
        path.write_bytes(stable_json({"releases": []}))
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with TestClient(app):
            pytest.fail("Startup must require a nonempty, valid active selection")


@pytest.mark.parametrize("kind", ["draft", "approved-candidate", "research-dossier"])
def test_nonpublished_inputs_cannot_be_selected_as_active_releases(
    kind: str,
    supported_release: Path,
    select_releases: Callable[[list[Path]], Path],
) -> None:
    from fastapi.testclient import TestClient

    paths = {
        "draft": EXAMPLES / "synthetic-stage4-dossier.json",
        "approved-candidate": supported_release.parents[1] / "candidate",
        "research-dossier": ROOT / "curation/alcohol_flush/stage2-draft.json",
    }
    if kind == "approved-candidate":
        assert (paths[kind] / "approval.json").is_file()
        assert not (paths[kind] / "checksums.json").exists()
    select_releases([paths[kind]])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with TestClient(app):
            pytest.fail(f"Startup accepted {kind} as a published release")
