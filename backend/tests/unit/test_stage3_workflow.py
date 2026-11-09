"""Synthetic approvals only; the real dossier is used for read-only review examples."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.models.curation import (
    ExplanationContent,
    ReviewAction,
    TraitCandidate,
    TraitDossier,
)
from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import TraitCatalog
from backend.services.trait_curation.cli import main
from backend.services.trait_curation.workflow import (
    ReviewScope,
    ScopedReviewDecision,
    content_depends_on_model,
    effective_review_status,
    get_snapshot,
    initialize_workspace,
    inspect_item,
    load_dossier,
    read_workspace,
    record_decision,
    review_targets,
    revise_workspace,
    workspace_history,
    workspace_status,
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = (ReviewScope.EVIDENCE, "synthetic-finding")
CLAIM = (ReviewScope.CLAIM, "synthetic-reviewed-claim")
MODEL = (ReviewScope.MODEL, "synthetic_education")
CONTENT = (ReviewScope.CONTENT, "synthetic-explanation")


@pytest.fixture
def dossier() -> TraitDossier:
    data = json.loads(
        (ROOT / "curation/examples/synthetic-reviewed-catalog.json").read_text(
            encoding="utf-8"
        )
    )["traits"][0]
    data["candidate"]["status"] = "draft"
    data["claims"][0].update(status="pending", assessment=None)
    data["explanations"][0]["reviewed"] = False
    return TraitDossier.model_validate(data)


@pytest.fixture
def allele_dossier(dossier: TraitDossier) -> TraitDossier:
    data = dossier.model_dump(mode="json")
    data["interpretation"] = {
        "strategy": "allele_count",
        "claim_ids": [CLAIM[1]],
        "requirements": {
            "rsid": "rs12345678",
            "placements": [
                {
                    "genome_build": "GRCh38",
                    "chromosome": "1",
                    "position": 101,
                    "sequence_accession": "NC_000001.11",
                }
            ],
            "orientation": "forward_genomic",
            "coordinate_system": "1-based",
            "ploidy": 2,
            "alleles": ["A", "G"],
        },
        "counted_allele": "A",
        "rules": [
            {"genotype": "GG", "copies": 0},
            {"genotype": "AG", "copies": 1},
            {"genotype": "AA", "copies": 2},
        ],
        "unavailable_policy": "withhold",
    }
    data["explanations"].extend(
        [
            {
                "content_id": "result",
                "kind": "outcome_summary",
                "body": "Fictional result with one copy.",
                "claim_ids": [CLAIM[1]],
                "result_key": "1",
            },
            {
                "content_id": "calculation",
                "kind": "calculation_notes",
                "body": "Count the specified allele only for compatible calls.",
                "claim_ids": [CLAIM[1]],
            },
            {
                "content_id": "model-wording",
                "kind": "simple_summary",
                "body": "This fictional model describes allele copies.",
                "claim_ids": [CLAIM[1]],
                "model_dependent": True,
            },
        ]
    )
    return TraitDossier.model_validate(data)


def decide(
    workspace: Path,
    key: tuple[ReviewScope, str],
    action: ReviewAction = ReviewAction.APPROVE,
) -> ScopedReviewDecision:
    inspected = inspect_item(get_snapshot(workspace).dossier, *key)
    return record_decision(
        workspace,
        *key,
        action,
        reviewer_id="synthetic-reviewer",
        rationale="Fictional acceptance test; no real scientific approval.",
        revision=inspected["revision"],
        fingerprint=inspected["fingerprint"],
    )


def approve_all(workspace: Path) -> None:
    for key in review_targets(get_snapshot(workspace).dossier):
        decide(workspace, key)


def states(workspace: Path) -> dict[tuple[str, str], str]:
    return {
        (item["scope"], item["target_id"]): item["state"]
        for item in workspace_status(workspace)["items"]
    }


def test_real_dossier_initialization_validation_and_inspection(tmp_path: Path) -> None:
    path = ROOT / "curation/alcohol_flush/stage2-draft.json"
    before = path.read_bytes()
    real = load_dossier(path)
    workspace = tmp_path / "real"
    initialize_workspace(workspace, real, "Initialize an unapproved research draft.")
    snapshot = get_snapshot(workspace)
    assert snapshot.dossier == real
    inspected = inspect_item(
        snapshot.dossier, ReviewScope.CLAIM, "rs671-function-draft"
    )
    claim = inspected["reviewed"]
    assert claim["payload"]["limitations"]
    evidence = claim["dependencies"]
    assert {item["payload"]["evidence_id"] for item in evidence} == {"E1", "E2", "E3"}
    assert evidence[0]["sources"][0]["source_id"] == "ncbi-refsnp-rs671"
    assert (
        "placements_with_allele" in evidence[0]["payload"]["source_location"]["locator"]
    )
    assert snapshot.dossier.explanations[0].model_dependent
    assert not workspace_status(workspace)["ready_for_stage4"]
    assert read_workspace(workspace)[1] == []
    assert path.read_bytes() == before


def test_model_dependency_field_defaults_and_validation(dossier: TraitDossier) -> None:
    data = dossier.explanations[0].model_dump(mode="json")
    del data["model_dependent"]  # Older Stage 2 JSON omits the field.
    content = ExplanationContent.model_validate(data)
    assert content.model_dependent is False
    assert not content_depends_on_model(content)
    explicit = ExplanationContent.model_validate({**data, "model_dependent": True})
    assert content_depends_on_model(explicit)
    with pytest.raises(ValidationError, match="model_dependent"):
        ExplanationContent.model_validate({**data, "model_dependent": "sometimes"})


def test_decisions_require_review_metadata() -> None:
    data = {
        "decision_id": "test-decision",
        "candidate_id": "synthetic",
        "candidate_revision": 1,
        "scope": "claim",
        "target_id": "claim",
        "action": "approve",
        "reviewer_id": "reviewer",
        "notes": "Synthetic rationale.",
        "fingerprint": "a" * 64,
        "created_at": "2026-11-08T00:00:00Z",
    }
    for field in (
        "candidate_revision",
        "scope",
        "target_id",
        "fingerprint",
        "reviewer_id",
        "notes",
        "created_at",
    ):
        incomplete = data.copy()
        del incomplete[field]
        with pytest.raises(ValidationError, match=field):
            ScopedReviewDecision.model_validate(incomplete)
    for field in ("reviewer_id", "notes"):
        with pytest.raises(ValidationError, match=field):
            ScopedReviewDecision.model_validate({**data, field: "   "})
    with pytest.raises(ValidationError, match="scope"):
        ScopedReviewDecision.model_validate({**data, "scope": "release"})
    decision = ScopedReviewDecision.model_validate(data)
    assert decision.created_at.utcoffset() is not None
    assert (
        ScopedReviewDecision.model_validate_json(decision.model_dump_json()) == decision
    )


def test_legacy_labels_do_not_supply_approval(tmp_path: Path) -> None:
    data = json.loads(
        (ROOT / "curation/examples/synthetic-reviewed-catalog.json").read_text(
            encoding="utf-8"
        )
    )
    labeled = TraitDossier.model_validate(data["traits"][0])
    initialize_workspace(tmp_path / "review", labeled, "Synthetic labels.")
    status = workspace_status(tmp_path / "review")
    assert not status["ready_for_stage4"]
    assert all(item["state"] == "pending" for item in status["items"])


@pytest.mark.parametrize("strategy", ["educational", "allele_count"])
def test_real_decisions_make_draft_ready_without_changing_labels(
    dossier: TraitDossier, allele_dossier: TraitDossier, strategy: str, tmp_path: Path
) -> None:
    draft = allele_dossier if strategy == "allele_count" else dossier
    workspace = tmp_path / "review"
    initialize_workspace(workspace, draft, "Synthetic draft.")
    approve_all(workspace)
    assert workspace_status(workspace)["ready_for_stage4"]
    saved = get_snapshot(workspace).dossier
    assert saved.candidate.status == "draft"
    assert saved.claims[0].status == "pending"
    assert all(not content.reviewed for content in saved.explanations)
    with pytest.raises(ValidationError):
        TraitCatalog.model_validate(
            {"schema_version": "3.1", "traits": [saved.model_dump()]}
        )


def test_latest_decisions_and_dependency_approval_are_separate(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    decide(workspace, CLAIM)
    assert states(workspace)[CLAIM] == "blocked"
    approve_all(workspace)
    decide(workspace, MODEL, ReviewAction.REJECT)
    current = states(workspace)
    assert current[CLAIM] == "approved"
    assert current[MODEL] == "rejected"
    assert current[CONTENT] == "approved"
    assert not workspace_status(workspace)["ready_for_stage4"]
    decide(workspace, MODEL)
    decide(workspace, EVIDENCE, ReviewAction.REQUEST_CHANGES)
    status = workspace_status(workspace)
    current = states(workspace)
    assert current[EVIDENCE] == "changes_requested"
    assert current[CLAIM] == "blocked"
    assert current[MODEL] == "blocked"
    assert not any(item["state"] == "stale" for item in status["decisions"])
    assert any(item["state"] == "superseded" for item in status["decisions"])
    decide(workspace, EVIDENCE)
    assert workspace_status(workspace)["ready_for_stage4"]


@pytest.mark.parametrize("correction", ["statement", "location", "source"])
def test_evidence_and_source_corrections_stale_dependent_approvals(
    dossier: TraitDossier, tmp_path: Path, correction: str
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    approve_all(workspace)
    corrected = get_snapshot(workspace).dossier
    if correction == "statement":
        corrected.evidence[0].statement = "Corrected fictional finding."
    elif correction == "location":
        corrected.evidence[0].source_location.section = "Corrected fictional location"
    else:
        corrected.sources[0].source_version = "Corrected fictional source version"
    revise_workspace(workspace, corrected, f"Correct {correction}.")
    status = workspace_status(workspace)
    assert all(item["state"] == "stale" for item in status["items"])
    assert all(item["state"] == "stale" for item in status["decisions"])
    assert not status["ready_for_stage4"]
    # Reapproving the finding alone cannot approve the changed dependent claims.
    decide(workspace, EVIDENCE)
    assert states(workspace)[CLAIM] == "stale"


def test_rule_changes_stale_only_model_and_model_dependent_content(
    allele_dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, allele_dossier, "Synthetic allele model.")
    approve_all(workspace)
    corrected = get_snapshot(workspace).dossier
    model = corrected.interpretation
    assert isinstance(model, AlleleCountInterpretation)
    model.counted_allele = "G"
    for rule in model.rules:
        rule.copies = rule.genotype.count("G")
    revise_workspace(workspace, corrected, "Count G instead.")
    current = states(workspace)
    assert current[EVIDENCE] == current[CLAIM] == current[CONTENT] == "approved"
    assert current[MODEL] == "stale"
    for target in ("result", "calculation", "model-wording"):
        assert current[("content", target)] == "stale"
    decide(workspace, MODEL, ReviewAction.REJECT)
    assert states(workspace)[CLAIM] == "approved"
    decide(workspace, (ReviewScope.CONTENT, "result"))
    assert states(workspace)[("content", "result")] == "blocked"
    assert not workspace_status(workspace)["ready_for_stage4"]


def test_wording_edit_preserves_other_text_and_scientific_approvals(
    allele_dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, allele_dossier, "Synthetic draft.")
    approve_all(workspace)
    corrected = get_snapshot(workspace).dossier
    corrected.explanations[0].body = "A clearer fictional explanation."
    revise_workspace(workspace, corrected, "Improve one explanation.")
    current = states(workspace)
    for key, state in current.items():
        assert state == ("stale" if key == CONTENT else "approved")
    decide(workspace, CONTENT)
    assert workspace_status(workspace)["ready_for_stage4"]


def test_independent_evidence_and_claims_remain_approved(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    data = dossier.model_dump(mode="json")
    data["evidence"].append({**data["evidence"][0], "evidence_id": "other-finding"})
    data["claims"].append(
        {
            **data["claims"][0],
            "claim_id": "other-claim",
            "evidence_ids": ["other-finding"],
        }
    )
    data["explanations"].append(
        {
            **data["explanations"][0],
            "content_id": "other-text",
            "claim_ids": ["other-claim"],
        }
    )
    workspace = tmp_path / "review"
    initialize_workspace(
        workspace, TraitDossier.model_validate(data), "Two independent claims."
    )
    approve_all(workspace)
    corrected = get_snapshot(workspace).dossier
    corrected.evidence[0].statement = "Correct only the first fictional finding."
    revise_workspace(workspace, corrected, "Correct first finding.")
    current = states(workspace)
    assert current[("evidence", "other-finding")] == "approved"
    assert current[("claim", "other-claim")] == "approved"
    assert current[("content", "other-text")] == "approved"
    assert current[MODEL] == "stale"


def test_history_numbering_and_overwrite_guards(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    dossier.candidate.revision = 7
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Imported revision seven.")
    original = (workspace / "revisions/0007.json").read_bytes()
    old_decision = decide(workspace, EVIDENCE)
    log = (workspace / "decisions.jsonl").read_bytes()
    corrected = get_snapshot(workspace).dossier
    corrected.evidence[0].statement = "Corrected fictional statement."
    saved = revise_workspace(workspace, corrected, "Correct source fidelity.")
    assert saved.dossier.candidate.revision == 8
    assert corrected.candidate.revision == 7  # Caller is not mutated.
    decide(workspace, EVIDENCE, ReviewAction.REQUEST_CHANGES)
    assert (workspace / "revisions/0007.json").read_bytes() == original
    assert (workspace / "decisions.jsonl").read_bytes().startswith(log)
    assert get_snapshot(workspace, 7).dossier == dossier
    history = workspace_history(workspace)
    assert [item["revision"] for item in history["revisions"]] == [7, 8]
    assert history["revisions"][1]["reason"] == "Correct source fidelity."
    assert history["decisions"][0]["decision_id"] == old_decision.decision_id
    with pytest.raises(FileExistsError):
        initialize_workspace(workspace, dossier, "Cannot overwrite.")
    with pytest.raises(ValueError, match="based on current revision 8"):
        revise_workspace(workspace, corrected, "Cannot submit an obsolete copy.")
    assert len(read_workspace(workspace)[0]) == 2


def test_inspected_revision_and_fingerprint_are_required_for_deciding(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    inspected = inspect_item(dossier, *EVIDENCE)
    with pytest.raises(ValueError, match="fingerprint changed"):
        record_decision(
            workspace,
            *EVIDENCE,
            ReviewAction.APPROVE,
            "reviewer",
            "Reason.",
            1,
            "0" * 64,
        )
    revise_workspace(workspace, dossier, "Unchanged scientific records.")
    with pytest.raises(ValueError, match="current revision changed"):
        record_decision(
            workspace,
            *EVIDENCE,
            ReviewAction.APPROVE,
            "reviewer",
            "Reason.",
            inspected["revision"],
            inspected["fingerprint"],
        )
    assert read_workspace(workspace)[1] == []


def test_formatting_and_revision_metadata_do_not_change_fingerprints(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    approve_all(workspace)
    original = {
        key: inspect_item(dossier, *key)["fingerprint"]
        for key in review_targets(dossier)
    }
    reformatted = TraitDossier.model_validate_json(
        json.dumps(dossier.model_dump(mode="json"), sort_keys=True, indent=4)
    )
    reformatted.candidate.reviewer_notes.append("Only workflow notes changed.")
    reformatted.candidate.pipeline_version = "manual-metadata-correction"
    revise_workspace(workspace, reformatted, "Formatting and metadata only.")
    current = get_snapshot(workspace).dossier
    assert {
        key: inspect_item(current, *key)["fingerprint"]
        for key in review_targets(current)
    } == original
    assert workspace_status(workspace)["ready_for_stage4"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proposed_name", "Corrected fictional display name"),
        ("proposed_category", "nutrition"),
        ("description", "Corrected fictional description."),
        ("keywords", ["fictional", "context"]),
    ],
)
def test_candidate_display_changes_require_only_content_review(
    allele_dossier: TraitDossier, tmp_path: Path, field: str, value: object
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, allele_dossier, "Synthetic draft.")
    approve_all(workspace)
    data = get_snapshot(workspace).dossier.model_dump(mode="json")
    data["candidate"][field] = value
    revise_workspace(workspace, TraitDossier.model_validate(data), f"Correct {field}.")
    status = workspace_status(workspace)
    assert not status["ready_for_stage4"]
    for item in status["items"]:
        expected = "stale" if item["scope"] == "content" else "approved"
        assert item["state"] == expected
    current = get_snapshot(workspace).dossier
    assert (
        inspect_item(current, *CONTENT)["reviewed"]["candidate_content"][field] == value
    )
    for content in current.explanations:
        decide(workspace, (ReviewScope.CONTENT, content.content_id))
    assert workspace_status(workspace)["ready_for_stage4"]


def test_restoring_exact_content_uses_latest_decision_for_that_fingerprint(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    approve_all(workspace)
    changed = get_snapshot(workspace).dossier
    changed.explanations[0].body = "A different proposal."
    revise_workspace(workspace, changed, "Propose different wording.")
    decide(workspace, CONTENT, ReviewAction.REJECT)
    restored = get_snapshot(workspace).dossier
    restored.explanations[0].body = dossier.explanations[0].body
    revise_workspace(workspace, restored, "Restore the originally reviewed wording.")
    assert workspace_status(workspace)["ready_for_stage4"]
    decide(workspace, CONTENT, ReviewAction.REQUEST_CHANGES)
    assert not workspace_status(workspace)["ready_for_stage4"]


def test_incomplete_and_structurally_incompatible_dossiers_are_not_ready(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    empty = TraitDossier(
        candidate=TraitCandidate(
            candidate_id="empty", proposed_id="empty", proposed_name="Empty"
        )
    )
    assert not effective_review_status(empty, [])["ready_for_stage4"]
    data = dossier.model_dump(mode="json")
    data["explanations"][0].update(kind="outcome_summary", result_key="1")
    workspace = tmp_path / "review"
    initialize_workspace(
        workspace, TraitDossier.model_validate(data), "Incomplete semantics."
    )
    approve_all(workspace)
    status = workspace_status(workspace)
    assert all(item["effective_approval"] for item in status["items"])
    assert (
        "educational entries cannot have result content" in status["structural_errors"]
    )
    assert not status["ready_for_stage4"]
    missing_model = get_snapshot(workspace).dossier
    missing_model.interpretation = None
    revise_workspace(workspace, missing_model, "Remove model.")
    decide(workspace, CONTENT)
    assert states(workspace)[CONTENT] == "blocked"


def test_invalid_corrections_and_missing_references_do_not_create_revisions(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    dossier.claims[0].evidence_ids = ["missing"]
    with pytest.raises(ValidationError, match="reference missing"):
        revise_workspace(workspace, dossier, "Broken reference.")
    with pytest.raises(ValidationError, match="reference missing"):
        initialize_workspace(tmp_path / "invalid", dossier, "Broken reference.")
    assert not (tmp_path / "invalid").exists()
    assert len(read_workspace(workspace)[0]) == 1
    with pytest.raises(ValidationError, match="reason"):
        revise_workspace(workspace, get_snapshot(workspace).dossier, "  ")
    assert len(read_workspace(workspace)[0]) == 1


def test_unicode_line_separator_in_rationale_preserves_decision_history(
    dossier: TraitDossier, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    inspected = inspect_item(dossier, *EVIDENCE)
    rationale = "Fictional evidence checked.\u2028Location verified."
    decision = record_decision(
        workspace,
        *EVIDENCE,
        ReviewAction.APPROVE,
        reviewer_id="synthetic-reviewer",
        rationale=rationale,
        revision=inspected["revision"],
        fingerprint=inspected["fingerprint"],
    )
    assert read_workspace(workspace)[1] == [decision]

    assert main(["status", str(workspace), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["items"][0]["effective_approval"]
    assert status["items"][0]["decision"]["notes"] == rationale

    assert main(["history", str(workspace)]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["decisions"] == [decision.model_dump(mode="json")]


@pytest.mark.parametrize("changed_record", ["evidence", "candidate"])
def test_altered_reviewed_snapshots_are_rejected(
    dossier: TraitDossier, tmp_path: Path, changed_record: str
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    decide(workspace, EVIDENCE if changed_record == "evidence" else CONTENT)
    path = workspace / "revisions/0001.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if changed_record == "evidence":
        snapshot["dossier"]["evidence"][0]["statement"] = "An out-of-band alteration."
    else:
        snapshot["dossier"]["candidate"]["proposed_name"] = "An out-of-band alteration."
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint disagrees"):
        workspace_status(workspace)


def test_incomplete_decision_log_is_rejected(
    dossier: TraitDossier, tmp_path: Path
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Synthetic draft.")
    decide(workspace, EVIDENCE)
    log_path = workspace / "decisions.jsonl"
    log_path.write_text(log_path.read_text(encoding="utf-8").rstrip(), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        workspace_history(workspace)


def test_cli_review_correction_and_history(
    dossier: TraitDossier, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "input.json"
    source.write_text(dossier.model_dump_json(), encoding="utf-8")
    workspace = tmp_path / "review"
    assert main(["init", str(source), str(workspace)]) == 0
    capsys.readouterr()
    assert main(["validate", str(workspace)]) == 0
    assert json.loads(capsys.readouterr().out)["valid_draft"]
    assert main(["inspect", str(workspace), "claim", CLAIM[1]]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert "Fictional study" in json.dumps(inspected)
    assert (
        main(
            [
                "decide",
                str(workspace),
                "claim",
                CLAIM[1],
                "approve",
                "--reviewer",
                "synthetic-reviewer",
                "--rationale",
                "Fictional test only.",
                "--revision",
                str(inspected["revision"]),
                "--fingerprint",
                inspected["fingerprint"],
            ]
        )
        == 0
    )
    assert dossier.claims[0].statement in capsys.readouterr().out
    assert main(["status", str(workspace)]) == 0
    assert "blocked" in capsys.readouterr().out
    exported = tmp_path / "correction.json"
    assert main(["inspect", str(workspace), "--output", str(exported)]) == 0
    capsys.readouterr()
    with pytest.raises(SystemExit) as error:
        main(["inspect", str(workspace), "--output", str(exported)])
    assert error.value.code == 2
    capsys.readouterr()
    corrected = load_dossier(exported)
    corrected.explanations[0].body = "A corrected fictional explanation."
    exported.write_text(corrected.model_dump_json(), encoding="utf-8")
    assert (
        main(["revise", str(workspace), str(exported), "--reason", "Improve wording."])
        == 0
    )
    capsys.readouterr()
    assert main(["inspect", str(workspace), "--revision", "1"]) == 0
    assert (
        json.loads(capsys.readouterr().out)["explanations"][0]["body"]
        == dossier.explanations[0].body
    )
    assert main(["history", str(workspace)]) == 0
    history = json.loads(capsys.readouterr().out)
    assert len(history["revisions"]) == 2 and len(history["decisions"]) == 1
    assert main(["status", str(workspace), "--json"]) == 0
    assert not json.loads(capsys.readouterr().out)["ready_for_stage4"]
    with pytest.raises(SystemExit) as error:
        main(["inspect", str(workspace), "claim", "missing"])
    assert error.value.code == 2
    assert "Unknown claim target" in capsys.readouterr().err
    source.write_text('{"candidate": {}}', encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["validate", str(source)])
    assert error.value.code == 2


def test_cli_module_entrypoint() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "backend.services.trait_curation.cli", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "init,validate,inspect,decide,revise,status,history" in result.stdout
    for command in ("build", "preview", "approve-release", "publish", "verify-release"):
        assert command in result.stdout
