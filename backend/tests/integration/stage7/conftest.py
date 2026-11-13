"""Real, temporary Stage 3/4 publications; all decisions are fictional."""

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from backend.models.curation import ReviewAction, TraitDossier
from backend.models.published_catalog import PublishedTrait, TraitCatalog
from backend.services.trait_curation.compiler import (
    approve_release,
    build_candidate,
    preview_candidate,
    publish_candidate,
    stable_json,
    verify_release,
)
from backend.services.trait_curation.workflow import (
    initialize_workspace,
    inspect_item,
    load_dossier,
    record_decision,
    review_targets,
)

ROOT = Path(__file__).resolve().parents[4]
EXAMPLES = ROOT / "curation/examples"
SAVED_RELEASE = ROOT / "data/releases/synthetic-stage4-demo-v1"
SUPPORTED_ID = "synthetic_stage7_allele"
SELECTION_ENV = "WHOAMI_ACTIVE_RELEASE_SET"


def publish_fictional(
    dossier: TraitDossier, cases: Path, directory: Path, release_id: str
) -> Path:
    """Use the existing workflow, including exact-item and final-file approval."""
    workspace = directory / "review"
    initialize_workspace(workspace, dossier, "Fictional Stage 7 software test only.")
    for scope, target in review_targets(dossier):
        item = inspect_item(dossier, scope, target)
        record_decision(
            workspace,
            scope,
            target,
            ReviewAction.APPROVE,
            "synthetic-stage7-reviewer",
            "Fictional test; no real scientific approval.",
            item["revision"],
            item["fingerprint"],
        )
    candidate = directory / "candidate"
    build_candidate(workspace, candidate, release_id, cases)
    preview, fingerprint = preview_candidate(candidate)
    assert dossier.candidate.proposed_name in preview
    approve_release(
        candidate,
        workspace,
        "synthetic-stage7-reviewer",
        "Checked the fictional preview and independent cases for this test.",
        fingerprint,
    )
    release = publish_candidate(candidate, workspace, directory / "releases")
    assert verify_release(release).release_id == release_id
    return release


@pytest.fixture(scope="module")
def saved_release() -> Path:
    verify_release(SAVED_RELEASE)
    return SAVED_RELEASE


@pytest.fixture(scope="module")
def supported_release(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("stage7-build37")
    dossier = load_dossier(EXAMPLES / "synthetic-stage4-dossier.json")
    dossier.candidate.candidate_id = "synthetic-stage7-build37"
    dossier.candidate.proposed_id = SUPPORTED_ID
    dossier.candidate.proposed_name = "Fictional Build 37 allele-count example"
    # Change the authoring input BEFORE review/build; never patch a release.
    data = dossier.model_dump(mode="json")
    placement = data["interpretation"]["requirements"]["placements"][0]
    placement.update(genome_build="GRCh37", sequence_accession="NC_000001.10")
    dossier = TraitDossier.model_validate(data)

    # Reuse independently authored arithmetic/error expectations. Only the
    # fictional trait identity and compatible reference representation change.
    cases = json.loads((EXAMPLES / "synthetic-stage4-cases.json").read_bytes())
    cases.update(trait_id=SUPPORTED_ID, case_set_id="fictional-stage7-build37-v1")
    for case in cases["cases"]:
        observation = case.get("observation")
        if observation is not None:
            if observation.get("genome_build") == "GRCh38":
                observation["genome_build"] = "GRCh37"
            observation["sequence_accession"] = "NC_000001.10"
    cases_path = directory / "cases.json"
    cases_path.write_bytes(stable_json(cases))
    return publish_fictional(dossier, cases_path, directory, "synthetic-stage7-v1")


@pytest.fixture(scope="module")
def supported_trait(supported_release: Path) -> PublishedTrait:
    return TraitCatalog.model_validate_json(
        (supported_release / "catalog.json").read_bytes()
    ).traits[0]


@pytest.fixture(scope="module")
def second_version_release(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return publish_fictional(
        load_dossier(EXAMPLES / "synthetic-stage4-dossier.json"),
        EXAMPLES / "synthetic-stage4-cases.json",
        tmp_path_factory.mktemp("stage7-second-version"),
        "synthetic-stage7-second-version-v1",
    )


@pytest.fixture(scope="module")
def educational_release(tmp_path_factory: pytest.TempPathFactory) -> Path:
    data = json.loads((EXAMPLES / "synthetic-reviewed-catalog.json").read_bytes())[
        "traits"
    ][0]
    data["candidate"].update(
        proposed_category="nutrition", description="Fictional education only."
    )
    # The old descriptive approval labels grant nothing: publish_fictional
    # records all effective Stage 3 decisions and performs Stage 4 publication.
    return publish_fictional(
        TraitDossier.model_validate(data),
        EXAMPLES / "synthetic-educational-cases.json",
        tmp_path_factory.mktemp("stage7-education"),
        "synthetic-stage7-education-v1",
    )


@pytest.fixture
def select_releases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[list[Path]], Path]:
    def select(paths: list[Path]) -> Path:
        selection = tmp_path / "active-releases.json"
        selection.write_bytes(
            stable_json(
                {
                    "releases": [
                        (
                            os.path.relpath(path, selection.parent)
                            if path.anchor.lower() == selection.anchor.lower()
                            else str(path)
                        )
                        for path in paths
                    ]
                }
            )
        )
        monkeypatch.setenv(SELECTION_ENV, str(selection))
        return selection

    return select


@pytest.fixture
def client(
    saved_release: Path,
    supported_release: Path,
    select_releases: Callable[[list[Path]], Path],
) -> Iterator[Any]:
    # Import here so a missing HTTP test dependency gives an assertion instead
    # of making the whole suite fail collection.
    try:
        from fastapi.testclient import TestClient
    except (ImportError, RuntimeError) as error:
        pytest.fail(f"HTTP test dependency missing: install httpx ({error})")
    from backend.main import app

    select_releases([saved_release, supported_release])
    with TestClient(app, raise_server_exceptions=False) as active_client:
        yield active_client


@pytest.fixture
def dna_text() -> str:
    return (ROOT / "backend/tests/dna_samples/stage6/23andme_build37.txt").read_text(
        encoding="utf-8"
    )
