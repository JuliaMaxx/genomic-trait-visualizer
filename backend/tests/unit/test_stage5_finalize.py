"""The consolidated CLI uses Stage 4 gates; all review decisions are fictional."""

import json
import shutil
from pathlib import Path

import pytest

from backend.models.curation import EvidenceClaim, EvidenceSource, ReviewAction
from backend.models.interpretation import EducationalInterpretation
from backend.models.research import ResearchRequest
from backend.services.trait_curation import research_sources
from backend.services.trait_curation.cli import main
from backend.services.trait_curation.compiler import sha256, stable_json, verify_release
from backend.services.trait_curation.research import acquisition_root, replay
from backend.services.trait_curation.research_sources import acquire
from backend.services.trait_curation.workflow import (
    ReviewScope,
    get_snapshot,
    initialize_workspace,
    inspect_item,
    load_dossier,
    record_decision,
    review_targets,
    revise_workspace,
)

EXAMPLES = Path(__file__).resolve().parents[3] / "curation/examples"
CASES = EXAMPLES / "synthetic-stage4-cases.json"


@pytest.fixture
def reviewed_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "review"
    dossier = load_dossier(EXAMPLES / "synthetic-stage4-dossier.json")
    initialize_workspace(workspace, dossier, "Fictional finalization test.")
    approve_all(workspace)
    return workspace


def finalize_args(workspace: Path, tmp_path: Path, cases: Path = CASES) -> list[str]:
    return [
        "finalize",
        str(workspace),
        str(tmp_path / "candidate"),
        "--release-id",
        "stage5-finalize-test",
        "--cases",
        str(cases),
        "--reviewer",
        "synthetic-release-reviewer",
        "--rationale",
        "Inspected the fictional preview and manifest.",
        "--releases",
        str(tmp_path / "releases"),
    ]


def test_finalize_still_supports_manual_stage4_workspaces(
    reviewed_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "publish")
    assert main(finalize_args(reviewed_workspace, tmp_path)) == 0
    assert (
        verify_release(tmp_path / "releases/stage5-finalize-test").trait_id
        == "synthetic_allele"
    )


@pytest.mark.parametrize("problem", ["missing", "stale", "cases"])
def test_finalize_prerequisites_fail_before_confirmation(
    reviewed_workspace: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    problem: str,
) -> None:
    workspace, cases = reviewed_workspace, CASES
    expected = "Stage 3 review is not ready"
    if problem == "missing":
        workspace = tmp_path / "unreviewed"
        initialize_workspace(
            workspace, get_snapshot(reviewed_workspace).dossier, "No approvals."
        )
    elif problem == "stale":
        dossier = get_snapshot(workspace).dossier
        dossier.evidence[0].statement += " Changed scientific finding."
        revise_workspace(workspace, dossier, "Fictional change after approval.")
    else:
        data = json.loads(CASES.read_bytes())
        # A structurally valid expectation disagrees with the fictional GG case.
        data["cases"][0]["expected"]["copies"] = 1
        cases = tmp_path / "failed-cases.json"
        cases.write_bytes(stable_json(data))
        expected = "Independent cases failed"

    def unexpected_prompt(prompt: str) -> str:
        raise AssertionError(
            "A failed prerequisite must not request release confirmation"
        )

    monkeypatch.setattr("builtins.input", unexpected_prompt)
    with pytest.raises(SystemExit) as error:
        main(finalize_args(workspace, tmp_path, cases))
    assert error.value.code == 2
    assert expected in capsys.readouterr().err
    assert not (tmp_path / "candidate").exists()
    assert not (tmp_path / "releases").exists()


@pytest.mark.parametrize("answer", ["no", "", "eof"])
def test_finalize_decline_leaves_candidate_unapproved(
    reviewed_workspace: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answer: str,
) -> None:
    def decline(prompt: str) -> str:
        if answer == "eof":
            raise EOFError
        return answer

    monkeypatch.setattr("builtins.input", decline)
    assert main(finalize_args(reviewed_workspace, tmp_path)) == 1
    assert (tmp_path / "candidate/manifest.json").exists()
    assert not (tmp_path / "candidate/approval.json").exists()
    assert not (tmp_path / "releases").exists()


def test_finalize_rechecks_approvals_after_confirmation(
    reviewed_workspace: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def confirm_after_edit(prompt: str) -> str:
        dossier = get_snapshot(reviewed_workspace).dossier
        dossier.evidence[0].statement += " Changed while inspecting the preview."
        revise_workspace(
            reviewed_workspace, dossier, "Fictional concurrent review edit."
        )
        return "publish"

    monkeypatch.setattr("builtins.input", confirm_after_edit)
    with pytest.raises(SystemExit) as error:
        main(finalize_args(reviewed_workspace, tmp_path))
    assert error.value.code == 2
    assert not (tmp_path / "candidate/approval.json").exists()
    assert not (tmp_path / "releases").exists()


def approve_all(workspace: Path) -> None:
    dossier = get_snapshot(workspace).dossier
    for scope, target in review_targets(dossier):
        inspected = inspect_item(dossier, scope, target)
        record_decision(
            workspace,
            scope,
            target,
            ReviewAction.APPROVE,
            "synthetic-reviewer",
            "Fictional workflow test; no scientific endorsement.",
            inspected["revision"],
            inspected["fingerprint"],
        )


@pytest.fixture
def reviewed_research(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Acquire fictional records, then supply explicit fictional human decisions."""
    association = {
        "association_id": 1,
        "reported_trait": ["Fictional teaching trait"],
        "efo_traits": [{"efo_id": "EFO_9999999"}],
        "snp_allele": [{"rs_id": "rs12345678", "effect_allele": "A"}],
        "multi_snp_haplotype": False,
        "snp_interaction": False,
        "accession_id": "GCST9999999",
        "pubmed_id": 9990001,
    }

    def fetch(url: str) -> tuple[int, bytes]:
        data: dict[str, object]
        if "/efo-traits?" in url:
            data = {
                "_embedded": {
                    "efo_traits": [
                        {"efo_id": "EFO_9999999", "efo_trait": "Synthetic education"}
                    ]
                }
            }
        elif "/associations?" in url:
            data = {
                "_embedded": {
                    "associations": [association, {**association, "association_id": 2}]
                }
            }
        elif "/studies/" in url:
            data = {
                "accession_id": "GCST9999999",
                "pubmed_id": 9990001,
                "initial_sample_size": "100 fictional participants",
            }
        elif "EXT_ID" in url:
            data = {
                "resultList": {
                    "result": [
                        {
                            "id": "9990001",
                            "pmid": "9990001",
                            "source": "MED",
                            "title": "Fictional teaching study",
                            "pubYear": "2020",
                        }
                    ]
                }
            }
        else:
            assert "TITLE_ABS" in url
            data = {"resultList": {"result": []}}
        return 200, stable_json(data)

    monkeypatch.setattr(research_sources, "fetch", fetch)
    root, workspace = tmp_path / "run", tmp_path / "research-review"
    acquire(ResearchRequest(trait_name="Synthetic education"), root)
    proposal = root / "proposal"
    dossier = replay(root, proposal)
    initialize_workspace(workspace, dossier, "Fictional research publication test.")
    completed = get_snapshot(workspace).dossier
    completed.candidate.proposed_category = "nutrition"
    completed.interpretation = EducationalInterpretation(
        strategy="educational", claim_ids=[completed.claims[0].claim_id]
    )
    revise_workspace(workspace, completed, "Fictional human educational-only choice.")
    approve_all(workspace)
    return workspace, proposal, EXAMPLES / "synthetic-educational-cases.json"


def research_args(reviewed: tuple[Path, Path, Path], tmp_path: Path) -> list[str]:
    workspace, proposal, cases = reviewed
    return finalize_args(workspace, tmp_path, cases) + [
        "--acquisition",
        str(proposal / "acquisition.json"),
    ]


@pytest.mark.parametrize(
    ("workflow", "problem"),
    [
        ("finalize", "response"),
        ("separate", "response"),
        ("finalize", "inventory-hash"),
        ("separate", "inventory-hash"),
        ("finalize", "inventory-url"),
        ("finalize", "inventory-identity"),
        ("finalize", "dossier-hash"),
        ("finalize", "missing-run"),
        ("finalize", "origin"),
        ("finalize", "missing-inventory-row"),
        ("finalize", "changed-review-origin"),
    ],
)
def test_build_paths_reject_inconsistent_research(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    workflow: str,
    problem: str,
) -> None:
    workspace, proposal, _ = reviewed_research
    root = acquisition_root(proposal)
    inventory_path = proposal / "acquisition.json"
    inventory = json.loads(inventory_path.read_bytes())
    expected = "Acquisition inventory disagrees"
    if problem == "response":
        path = root / inventory[0]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        expected = "Source hash mismatch"
    elif problem == "inventory-hash":
        inventory[0]["sha256"] = "0" * 64
    elif problem == "inventory-url":
        inventory[0]["url"] += "&tampered=true"
    elif problem == "inventory-identity":
        inventory[0]["document_id"] = "fabricated-document"
    elif problem == "dossier-hash":
        dossier = get_snapshot(workspace).dossier
        dossier.sources[0].source_version = "sha256:" + "0" * 64
        revise_workspace(workspace, dossier, "Fictional incorrect source hash.")
        approve_all(workspace)
        expected = "Dossier source disagrees"
    elif problem == "missing-run":
        (root / "run.json").unlink()
        expected = "Saved acquisition run missing"
    elif problem == "origin":
        # Rewriting the supplied metadata cannot replace the reviewed origin.
        metadata_path = proposal / "processing.json"
        metadata = json.loads(metadata_path.read_bytes())
        metadata["run_sha256"] = "0" * 64
        metadata_path.write_bytes(stable_json(metadata))
        expected = "does not match the reviewed Stage 5 origin"
    elif problem == "missing-inventory-row":
        inventory.pop(0)
        expected = "missing published sources"
    elif problem == "changed-review-origin":
        dossier = get_snapshot(workspace).dossier
        dossier.candidate.research_run_sha256 = "0" * 64
        revise_workspace(workspace, dossier, "Fictional attempted origin replacement.")
        approve_all(workspace)
        expected = "acquisition-run identity changed"
    inventory_path.write_bytes(stable_json(inventory))
    args = (research_args if workflow == "finalize" else separate_build_args)(
        reviewed_research, tmp_path
    )

    def unexpected_prompt(prompt: str) -> str:
        raise AssertionError("Inconsistent acquisition must fail before confirmation")

    monkeypatch.setattr("builtins.input", unexpected_prompt)
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert expected in capsys.readouterr().err
    assert not (tmp_path / "candidate").exists()
    assert not (tmp_path / "releases").exists()


@pytest.mark.parametrize(
    "problem", ["response", "inventory", "inventory-version", "run-and-metadata"]
)
def test_research_integrity_is_rechecked_after_confirmation(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    problem: str,
) -> None:
    _, proposal, _ = reviewed_research
    root = acquisition_root(proposal)

    def change_during_confirmation(prompt: str) -> str:
        inventory_path = proposal / "acquisition.json"
        inventory = json.loads(inventory_path.read_bytes())
        if problem == "response":
            path = root / inventory[0]["path"]
            path.write_bytes(path.read_bytes() + b" ")
        elif problem == "inventory":
            inventory[0]["sha256"] = "0" * 64
            inventory_path.write_bytes(stable_json(inventory))
        elif problem == "inventory-version":
            inventory[0]["version"] = "changed-after-preview"
            inventory_path.write_bytes(stable_json(inventory))
        else:
            # Matching rewritten files/metadata still differ from the review anchor.
            path = root / "run.json"
            path.write_bytes(path.read_bytes() + b" ")
            metadata_path = proposal / "processing.json"
            metadata = json.loads(metadata_path.read_bytes())
            metadata["run_sha256"] = sha256(path.read_bytes())
            metadata_path.write_bytes(stable_json(metadata))
        return "publish"

    monkeypatch.setattr("builtins.input", change_during_confirmation)
    with pytest.raises(SystemExit) as error:
        main(research_args(reviewed_research, tmp_path))
    assert error.value.code == 2
    assert not (tmp_path / "candidate/approval.json").exists()
    assert not (tmp_path / "releases").exists()


def test_research_rejected_and_removed_evidence_does_not_need_publication(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _ = reviewed_research
    dossier = get_snapshot(workspace).dossier
    removed_evidence, removed_claim, removed_source = (
        dossier.evidence[0].evidence_id,
        dossier.claims[0].claim_id,
        dossier.sources[0].source_id,
    )
    inspected = inspect_item(dossier, ReviewScope.EVIDENCE, removed_evidence)
    record_decision(
        workspace,
        ReviewScope.EVIDENCE,
        removed_evidence,
        ReviewAction.REJECT,
        "synthetic-reviewer",
        "Fictional decision to exclude this record.",
        inspected["revision"],
        inspected["fingerprint"],
    )
    dossier.evidence = [
        e for e in dossier.evidence if e.evidence_id != removed_evidence
    ]
    dossier.claims = [c for c in dossier.claims if c.claim_id != removed_claim]
    dossier.explanations = [
        text for text in dossier.explanations if removed_claim not in text.claim_ids
    ]
    dossier.sources = [s for s in dossier.sources if s.source_id != removed_source]
    dossier.candidate.evidence_ids.remove(removed_evidence)
    dossier.candidate.source_ids.remove(removed_source)
    assert dossier.interpretation is not None
    dossier.interpretation.claim_ids = [dossier.claims[0].claim_id]
    revise_workspace(workspace, dossier, "Remove rejected record and dependent text.")
    approve_all(workspace)
    monkeypatch.setattr("builtins.input", lambda _: "publish")
    assert main(research_args(reviewed_research, tmp_path)) == 0
    release = tmp_path / "releases/stage5-finalize-test"
    verify_release(release)
    inputs = json.loads((release / "inputs.json").read_bytes())
    assert len(inputs["source_documents"]) == 3
    assert removed_source not in {
        row["source_id"] for row in inputs["source_documents"]
    }


def separate_build_args(reviewed: tuple[Path, Path, Path], tmp_path: Path) -> list[str]:
    workspace, proposal, cases = reviewed
    return [
        "build",
        str(workspace),
        str(tmp_path / "candidate"),
        "--release-id",
        "stage5-finalize-test",
        "--cases",
        str(cases),
        "--acquisition",
        str(proposal / "acquisition.json"),
    ]


def separate_approval_args(
    reviewed: tuple[Path, Path, Path], tmp_path: Path
) -> list[str]:
    return [
        "approve-release",
        str(tmp_path / "candidate"),
        str(reviewed[0]),
        "--reviewer",
        "synthetic-release-reviewer",
        "--rationale",
        "Inspected the fictional preview.",
        "--fingerprint",
        sha256((tmp_path / "candidate/manifest.json").read_bytes()),
    ]


def separate_publish_args(
    reviewed: tuple[Path, Path, Path], tmp_path: Path
) -> list[str]:
    return [
        "publish",
        str(tmp_path / "candidate"),
        str(reviewed[0]),
        "--releases",
        str(tmp_path / "releases"),
    ]


@pytest.mark.parametrize("workflow", ["finalize", "separate"])
def test_both_publication_paths_publish_exact_reviewed_research(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    workflow: str,
) -> None:
    workspace, proposal, _ = reviewed_research
    candidate = tmp_path / "candidate"
    decisions = (workspace / "decisions.jsonl").read_bytes()
    frozen: dict[str, bytes] = {}

    def confirm(prompt: str) -> str:
        output = capsys.readouterr().out
        assert (candidate / "preview.md").read_text(encoding="utf-8") in output
        assert (
            f"Manifest SHA-256: {sha256((candidate / 'manifest.json').read_bytes())}"
            in output
        )
        assert "Type 'publish'" in prompt
        assert not (candidate / "approval.json").exists()
        assert not (tmp_path / "releases").exists()
        frozen.update({path.name: path.read_bytes() for path in candidate.iterdir()})
        return "publish"

    monkeypatch.setattr("builtins.input", confirm)
    if workflow == "finalize":
        assert main(research_args(reviewed_research, tmp_path)) == 0
    else:
        assert main(separate_build_args(reviewed_research, tmp_path)) == 0
        assert main(["preview", str(candidate)]) == 0
        frozen.update({path.name: path.read_bytes() for path in candidate.iterdir()})
        assert main(separate_approval_args(reviewed_research, tmp_path)) == 0
        assert main(separate_publish_args(reviewed_research, tmp_path)) == 0
    release = tmp_path / "releases/stage5-finalize-test"
    for name, raw in frozen.items():
        assert (candidate / name).read_bytes() == raw
        if name != "acquisition-link.json":
            assert (release / name).read_bytes() == raw
    assert (release / "approval.json").read_bytes() == (
        candidate / "approval.json"
    ).read_bytes()
    approval = json.loads((release / "approval.json").read_bytes())
    assert approval["manifest_sha256"] == sha256(frozen["manifest.json"])
    assert approval["reviewer_id"] == "synthetic-release-reviewer"
    assert (workspace / "decisions.jsonl").read_bytes() == decisions
    inputs = json.loads(frozen["inputs.json"])
    assert "research_acquisition_path" not in inputs
    link = json.loads(frozen["acquisition-link.json"])
    assert link["research_acquisition_path"] == str(
        (proposal / "acquisition.json").resolve()
    )
    assert not (release / "acquisition-link.json").exists()
    documents = inputs["source_documents"]
    assert len(documents) == 4
    inventory = json.loads((proposal / "acquisition.json").read_bytes())
    assert (
        inventory[0]["path"] == inventory[1]["path"]
    )  # Two association records, one response.
    dossier = get_snapshot(workspace).dossier
    inspected = inspect_item(
        dossier, ReviewScope.EVIDENCE, dossier.evidence[0].evidence_id
    )
    assert inspected["reviewed"]["research_run_sha256"] == sha256(
        (acquisition_root(proposal) / "run.json").read_bytes()
    )
    # Historical release verification does not require the original downloads.
    (acquisition_root(proposal) / "run.json").unlink()
    assert verify_release(release).trait_id == "synthetic_education"


def test_research_build_is_identical_at_different_acquisition_locations(
    reviewed_research: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    workspace, proposal, cases = reviewed_research
    copied_run = tmp_path / "different-location/run"
    shutil.copytree(acquisition_root(proposal), copied_run)
    relocated = (workspace, copied_run / "proposal", cases)
    other_build = tmp_path / "other-build"
    assert main(separate_build_args(reviewed_research, tmp_path)) == 0
    assert main(separate_build_args(relocated, other_build)) == 0
    for name in (
        "catalog.json",
        "inputs.json",
        "preview.md",
        "verification.json",
        "manifest.json",
    ):
        assert (tmp_path / "candidate" / name).read_bytes() == (
            other_build / "candidate" / name
        ).read_bytes(), name
    manifest = (tmp_path / "candidate/manifest.json").read_bytes()
    inputs = (tmp_path / "candidate/inputs.json").read_bytes()
    assert str(proposal).encode() not in inputs
    assert str(copied_run).encode() not in inputs
    # Relocating the verified inputs needs only a local locator update, not a new
    # payload or manifest approval fingerprint. The old target is now unavailable.
    (tmp_path / "candidate/acquisition-link.json").write_bytes(
        stable_json(
            {"research_acquisition_path": str(copied_run / "proposal/acquisition.json")}
        )
    )
    (acquisition_root(proposal) / "run.json").unlink()
    for reviewed, build_root in (
        (reviewed_research, tmp_path),
        (relocated, other_build),
    ):
        assert main(separate_approval_args(reviewed, build_root)) == 0
        assert main(separate_publish_args(reviewed, build_root)) == 0
        release = build_root / "releases/stage5-finalize-test"
        assert (release / "manifest.json").read_bytes() == manifest
        verify_release(release)


@pytest.mark.parametrize(
    ("point", "problem"),
    [
        ("approval", "response"),
        ("publish", "response"),
        ("publish", "inventory-hash"),
        ("publish", "missing-inventory"),
        ("publish", "missing-processing"),
        ("publish", "missing-run"),
        ("approval", "missing-link"),
        ("publish", "missing-link"),
    ],
)
def test_separate_approval_and_publication_recheck_research(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    point: str,
    problem: str,
) -> None:
    assert main(separate_build_args(reviewed_research, tmp_path)) == 0
    if point == "publish":
        assert main(separate_approval_args(reviewed_research, tmp_path)) == 0
    proposal = reviewed_research[1]
    root = acquisition_root(proposal)
    inventory_path = proposal / "acquisition.json"
    inventory = json.loads(inventory_path.read_bytes())
    manifest = (tmp_path / "candidate/manifest.json").read_bytes()
    if problem == "response":
        response = root / inventory[0]["path"]
        response.write_bytes(response.read_bytes() + b" ")
    elif problem == "inventory-hash":
        inventory[0]["sha256"] = "0" * 64
        inventory_path.write_bytes(stable_json(inventory))
    else:
        missing = {
            "missing-inventory": inventory_path,
            "missing-processing": proposal / "processing.json",
            "missing-run": root / "run.json",
            "missing-link": tmp_path / "candidate/acquisition-link.json",
        }[problem]
        missing.unlink()
    args = (separate_approval_args if point == "approval" else separate_publish_args)(
        reviewed_research, tmp_path
    )
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    if problem == "missing-link":
        assert "requires --acquisition" in capsys.readouterr().err
    assert (tmp_path / "candidate/manifest.json").read_bytes() == manifest
    if point == "approval":
        assert not (tmp_path / "candidate/approval.json").exists()
    assert not (tmp_path / "releases").exists()


@pytest.mark.parametrize("problem", ["argument", "origin", "processing"])
def test_separate_build_cannot_treat_missing_research_metadata_as_manual(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    problem: str,
) -> None:
    workspace, proposal, _ = reviewed_research
    args = separate_build_args(reviewed_research, tmp_path)
    if problem == "argument":
        args = args[:-2]
    elif problem == "origin":
        dossier = get_snapshot(workspace).dossier
        dossier.candidate.pipeline_version = "manual"
        dossier.candidate.research_run_sha256 = None
        revise_workspace(
            workspace, dossier, "Fictional removal of optional origin fields."
        )
        approve_all(workspace)
    else:
        (proposal / "processing.json").unlink()
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert not (tmp_path / "candidate").exists()
    assert not (tmp_path / "releases").exists()


def test_local_inventory_link_cannot_substitute_another_run(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(separate_build_args(reviewed_research, tmp_path)) == 0
    assert main(separate_approval_args(reviewed_research, tmp_path)) == 0
    copied_run = tmp_path / "other-run"
    shutil.copytree(acquisition_root(reviewed_research[1]), copied_run)
    run_path = copied_run / "run.json"
    run = json.loads(run_path.read_bytes())
    run["warnings"].append("Fictional different acquisition run.")
    run_path.write_bytes(stable_json(run))
    metadata_path = copied_run / "proposal/processing.json"
    metadata = json.loads(metadata_path.read_bytes())
    metadata["run_sha256"] = sha256(run_path.read_bytes())
    metadata_path.write_bytes(stable_json(metadata))
    (tmp_path / "candidate/acquisition-link.json").write_bytes(
        stable_json(
            {"research_acquisition_path": str(copied_run / "proposal/acquisition.json")}
        )
    )
    with pytest.raises(SystemExit) as error:
        main(separate_publish_args(reviewed_research, tmp_path))
    assert error.value.code == 2
    assert "does not match the reviewed Stage 5 origin" in capsys.readouterr().err
    assert not (tmp_path / "releases").exists()


def test_legacy_inputs_with_a_lookup_path_remain_readable(
    reviewed_research: tuple[Path, Path, Path],
    tmp_path: Path,
) -> None:
    assert main(separate_build_args(reviewed_research, tmp_path)) == 0
    candidate = tmp_path / "candidate"
    inputs_path = candidate / "inputs.json"
    inputs = json.loads(inputs_path.read_bytes())
    link_path = candidate / "acquisition-link.json"
    inputs.update(json.loads(link_path.read_bytes()))
    inputs_path.write_bytes(stable_json(inputs))
    link_path.unlink()
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"]["inputs.json"] = sha256(inputs_path.read_bytes())
    manifest_path.write_bytes(stable_json(manifest))
    assert main(separate_approval_args(reviewed_research, tmp_path)) == 0
    assert main(separate_publish_args(reviewed_research, tmp_path)) == 0
    (acquisition_root(reviewed_research[1]) / "run.json").unlink()
    verify_release(tmp_path / "releases/stage5-finalize-test")


@pytest.fixture
def research_with_supplement(
    reviewed_research: tuple[Path, Path, Path], tmp_path: Path
) -> tuple[Path, Path, Path]:
    workspace, proposal, _ = reviewed_research
    dossier = get_snapshot(workspace).dossier
    source = EvidenceSource.model_validate(
        {
            "source_id": "human-supplement",
            "source_type": "other",
            "name": "Fictional supplemental reference",
            "url": "https://example.org/fictional-reference",
            "source_version": "manual-v1",
        }
    )
    evidence = EvidenceClaim.model_validate(
        {
            "evidence_id": "human-evidence",
            "trait_id": dossier.candidate.proposed_id,
            "claim_type": "study_limitation",
            "statement": "Fictional supplemental teaching context.",
            "source_ids": [source.source_id],
            "source_location": {"locator": "Excerpt paragraph 1"},
            "extraction_method": "manual",
        }
    )
    dossier.sources.append(source)
    dossier.evidence.append(evidence)
    dossier.candidate.source_ids.append(source.source_id)
    dossier.candidate.evidence_ids.append(evidence.evidence_id)
    dossier.claims[0].evidence_ids.append(evidence.evidence_id)
    revise_workspace(workspace, dossier, "Human-added fictional supplemental evidence.")
    excerpt = tmp_path / "supplemental-excerpt.txt"
    excerpt.write_text("Fictional teaching context.\n", encoding="utf-8")
    inventory_path = proposal / "acquisition.json"
    inventory = json.loads(inventory_path.read_bytes())
    inventory.append(
        {
            "source_id": source.source_id,
            "document_id": "human-excerpt",
            "sha256": sha256(excerpt.read_bytes()),
            "type": "excerpt",
            # A document download URL can differ from its bibliographic citation URL.
            "url": "https://example.org/download/fictional-excerpt.txt",
            "version": "manual-v1",
            "path": str(excerpt),
        }
    )
    inventory_path.write_bytes(stable_json(inventory))
    return reviewed_research


@pytest.mark.parametrize("workflow", ["finalize", "separate"])
def test_reviewed_supplemental_source_can_publish(
    research_with_supplement: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    workflow: str,
) -> None:
    workspace, _, _ = research_with_supplement
    # The source and its dependent claim must pass the ordinary Stage 3 review.
    with pytest.raises(SystemExit) as error:
        main(separate_build_args(research_with_supplement, tmp_path))
    assert error.value.code == 2
    assert "Stage 3 review is not ready" in capsys.readouterr().err
    assert not (tmp_path / "candidate").exists()
    approve_all(workspace)
    monkeypatch.setattr("builtins.input", lambda _: "publish")
    if workflow == "finalize":
        assert main(research_args(research_with_supplement, tmp_path)) == 0
    else:
        assert main(separate_build_args(research_with_supplement, tmp_path)) == 0
        assert main(separate_approval_args(research_with_supplement, tmp_path)) == 0
        assert main(separate_publish_args(research_with_supplement, tmp_path)) == 0
    release = tmp_path / "releases/stage5-finalize-test"
    verify_release(release)
    inputs = json.loads((release / "inputs.json").read_bytes())
    assert {row["source_id"] for row in inputs["source_documents"]} == {
        "gwas-association-1",
        "gwas-study-GCST9999999",
        "europe-pmc-MED-9990001",
        "gwas-association-2",
        "human-supplement",
    }
    assert (
        next(
            row
            for row in inputs["source_documents"]
            if row["source_id"] == "human-supplement"
        )["type"]
        == "excerpt"
    )


@pytest.mark.parametrize(
    "problem",
    [
        "original-response",
        "original-inventory",
        "unreferenced-inventory",
        "after-build",
    ],
)
def test_supplements_preserve_acquisition_and_publication_checks(
    research_with_supplement: tuple[Path, Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    problem: str,
) -> None:
    workspace, proposal, _ = research_with_supplement
    approve_all(workspace)
    if problem == "after-build":
        assert main(separate_build_args(research_with_supplement, tmp_path)) == 0
        assert main(separate_approval_args(research_with_supplement, tmp_path)) == 0
    inventory_path = proposal / "acquisition.json"
    inventory = json.loads(inventory_path.read_bytes())
    expected = "Acquisition inventory disagrees"
    if problem == "original-response":
        response = acquisition_root(proposal) / inventory[0]["path"]
        response.write_bytes(response.read_bytes() + b" ")
        expected = "Source hash mismatch"
    elif problem == "original-inventory":
        inventory[0]["sha256"] = "0" * 64
    elif problem == "unreferenced-inventory":
        inventory.append(
            {
                **inventory[-1],
                "source_id": "not-reviewed",
                "document_id": "not-reviewed",
            }
        )
    else:
        inventory[-1]["sha256"] = "0" * 64
        expected = "Acquisition inventory changed"
    inventory_path.write_bytes(stable_json(inventory))
    args = (separate_publish_args if problem == "after-build" else separate_build_args)(
        research_with_supplement, tmp_path
    )
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert expected in capsys.readouterr().err
    assert not (tmp_path / "releases").exists()
