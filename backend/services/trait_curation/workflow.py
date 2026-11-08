"""Offline manual review. No publication, scientific scoring or DNA evaluation."""

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import AwareDatetime, Field

from backend.models.curation import (
    CurationModel,
    ExplanationContent,
    ReviewAction,
    ReviewDecision,
    Text,
    TraitDossier,
)
from backend.services.trait_curation.validation import (
    validate_dossier,
    validate_review_readiness,
)


class ReviewScope(StrEnum):
    EVIDENCE = "evidence"
    CLAIM = "claim"
    MODEL = "model"
    CONTENT = "content"


class ScopedReviewDecision(ReviewDecision):
    """Reuse review metadata, requiring an exact subject and a rationale (notes)."""

    scope: ReviewScope
    target_id: Text
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    notes: str = Field(min_length=1, max_length=4000)
    created_at: AwareDatetime


class RevisionSnapshot(CurationModel):
    reason: Text
    created_at: AwareDatetime
    dossier: TraitDossier


ReviewKey = tuple[ReviewScope, str]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def write_json_new(path: Path, value: object) -> None:
    """Exclusive creation prevents replacing a snapshot or an exported JSON copy."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )


def load_dossier(path: Path) -> TraitDossier:
    return validate_dossier(json.loads(path.read_text(encoding="utf-8-sig")))


def content_depends_on_model(content: ExplanationContent) -> bool:
    return (
        content.model_dependent
        or content.result_key is not None
        or content.kind in {"mental_model", "model_limit_summary", "calculation_notes"}
    )


def review_targets(dossier: TraitDossier) -> list[ReviewKey]:
    """Dependency order: evidence, claims, the one model, then individual texts."""
    targets: list[ReviewKey] = [
        (ReviewScope.EVIDENCE, item.evidence_id) for item in dossier.evidence
    ]
    targets.extend((ReviewScope.CLAIM, item.claim_id) for item in dossier.claims)
    if dossier.interpretation is not None:
        targets.append((ReviewScope.MODEL, dossier.candidate.proposed_id))
    targets.extend(
        (ReviewScope.CONTENT, item.content_id) for item in dossier.explanations
    )
    return targets


def _review_parts(
    dossier: TraitDossier, scope: ReviewScope, target_id: str
) -> tuple[dict[str, Any], list[ReviewKey], list[dict[str, Any]]]:
    """The four explicit dependency rules; sources have no separate approval scope."""
    if scope == ReviewScope.EVIDENCE:
        for finding in dossier.evidence:
            if finding.evidence_id == target_id:
                sources = [
                    source.model_dump(mode="json")
                    for source in dossier.sources
                    if source.source_id in finding.source_ids
                ]
                return finding.model_dump(mode="json"), [], sources
    elif scope == ReviewScope.CLAIM:
        for claim in dossier.claims:
            if claim.claim_id == target_id:
                return (
                    claim.model_dump(mode="json"),
                    [
                        (ReviewScope.EVIDENCE, ref)
                        for ref in sorted(set(claim.evidence_ids))
                    ],
                    [],
                )
    elif scope == ReviewScope.MODEL:
        model = dossier.interpretation
        if model is not None and target_id == dossier.candidate.proposed_id:
            return (
                model.model_dump(mode="json"),
                [(ReviewScope.CLAIM, ref) for ref in sorted(set(model.claim_ids))],
                [],
            )
    elif scope == ReviewScope.CONTENT:
        for content in dossier.explanations:
            if content.content_id == target_id:
                dependencies = [
                    (ReviewScope.CLAIM, ref) for ref in sorted(set(content.claim_ids))
                ]
                if content_depends_on_model(content):
                    dependencies.append(
                        (ReviewScope.MODEL, dossier.candidate.proposed_id)
                    )
                return content.model_dump(mode="json"), dependencies, []
    raise ValueError(f"Unknown {scope.value} target: {target_id}")


def _reviewed_data(
    dossier: TraitDossier, scope: ReviewScope, target_id: str
) -> dict[str, Any]:
    payload, dependencies, sources = _review_parts(dossier, scope, target_id)
    # A draft can contain model-related wording before a model is proposed.
    # Show the absence explicitly; status will block approval on this dependency.
    missing_model = dossier.interpretation is None and any(
        key[0] == ReviewScope.MODEL for key in dependencies
    )
    if missing_model:
        dependencies = [key for key in dependencies if key[0] != ReviewScope.MODEL]
    reviewed = {
        "candidate_id": dossier.candidate.candidate_id,
        "trait_id": dossier.candidate.proposed_id,
        "scope": scope.value,
        "target_id": target_id,
        "payload": payload,
        "sources": sources,
        "missing_model": missing_model,
        "dependencies": [
            _reviewed_data(dossier, dep_scope, dep_id)
            for dep_scope, dep_id in dependencies
        ],
    }
    if scope == ReviewScope.CONTENT:
        # Shared display context belongs to wording review, not scientific review.
        reviewed["candidate_content"] = dossier.candidate.model_dump(
            mode="json",
            include={"proposed_name", "proposed_category", "description", "keywords"},
        )
    return reviewed


def inspect_item(
    dossier: TraitDossier, scope: ReviewScope, target_id: str
) -> dict[str, Any]:
    dossier = validate_dossier(dossier)
    reviewed = _reviewed_data(dossier, ReviewScope(scope), target_id)
    fingerprint = hashlib.sha256(_canonical_json(reviewed).encode("utf-8")).hexdigest()
    return {
        "revision": dossier.candidate.revision,
        "fingerprint": fingerprint,
        "reviewed": reviewed,
    }


def initialize_workspace(
    workspace: Path, dossier: TraitDossier, reason: str
) -> RevisionSnapshot:
    snapshot = RevisionSnapshot(
        reason=reason,
        dossier=validate_dossier(dossier),
        created_at=datetime.now(timezone.utc),
    )
    # Preserve the incoming revision number, including a dossier already at N > 1.
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / "revisions").mkdir()
    _save_snapshot(workspace, snapshot)
    (workspace / "decisions.jsonl").touch(exist_ok=False)
    return snapshot


def _save_snapshot(workspace: Path, snapshot: RevisionSnapshot) -> None:
    path = workspace / "revisions" / f"{snapshot.dossier.candidate.revision:04d}.json"
    write_json_new(path, snapshot.model_dump(mode="json"))


def read_workspace(
    workspace: Path,
) -> tuple[list[RevisionSnapshot], list[ScopedReviewDecision]]:
    """Fail on malformed history rather than silently discarding review records."""
    paths = list((workspace / "revisions").glob("*.json"))
    if not paths:
        raise ValueError(f"No revision snapshots in {workspace}")
    snapshots: dict[int, RevisionSnapshot] = {}
    for path in paths:
        snapshot = RevisionSnapshot.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        revision = snapshot.dossier.candidate.revision
        if path.name != f"{revision:04d}.json" or revision in snapshots:
            raise ValueError(
                f"Snapshot filename must match revision {revision}: {path.name}"
            )
        snapshots[revision] = snapshot
    numbers = sorted(snapshots)
    if numbers != list(range(numbers[0], numbers[-1] + 1)):
        raise ValueError("Revision history has missing numbers")
    first = snapshots[numbers[0]].dossier.candidate
    for snapshot in snapshots.values():
        candidate = snapshot.dossier.candidate
        if (candidate.candidate_id, candidate.proposed_id) != (
            first.candidate_id,
            first.proposed_id,
        ):
            raise ValueError(
                "All revisions must belong to the same candidate and trait"
            )

    log = (workspace / "decisions.jsonl").read_text(encoding="utf-8")
    if log and not log.endswith("\n"):
        raise ValueError("Decision log is incomplete: its final newline is missing")
    decisions: list[ScopedReviewDecision] = []
    ids: set[str] = set()
    # Split only on LF and drop the empty item after the required final newline.
    for line_number, line in enumerate(log.split("\n")[:-1], 1):
        decision = ScopedReviewDecision.model_validate_json(line)
        if decision.decision_id in ids:
            raise ValueError(f"Duplicate decision ID on log line {line_number}")
        ids.add(decision.decision_id)
        reviewed_snapshot = snapshots.get(decision.candidate_revision)
        if reviewed_snapshot is None or decision.candidate_id != first.candidate_id:
            raise ValueError(
                f"Decision on line {line_number} references an unknown revision"
            )
        actual = inspect_item(
            reviewed_snapshot.dossier, decision.scope, decision.target_id
        )["fingerprint"]
        if decision.fingerprint != actual:
            raise ValueError(
                f"Decision fingerprint disagrees with snapshot on line {line_number}"
            )
        decisions.append(decision)
    return [snapshots[number] for number in numbers], decisions


def get_snapshot(workspace: Path, revision: int | None = None) -> RevisionSnapshot:
    snapshots, _ = read_workspace(workspace)
    if revision is None:
        return snapshots[-1]
    for snapshot in snapshots:
        if snapshot.dossier.candidate.revision == revision:
            return snapshot
    raise ValueError(f"Unknown revision: {revision}")


def revise_workspace(
    workspace: Path, corrected: TraitDossier, reason: str
) -> RevisionSnapshot:
    current = get_snapshot(workspace).dossier.candidate
    corrected = validate_dossier(corrected)
    candidate = corrected.candidate
    if (candidate.candidate_id, candidate.proposed_id) != (
        current.candidate_id,
        current.proposed_id,
    ):
        raise ValueError("A correction must keep the candidate and trait IDs")
    if candidate.revision != current.revision:
        raise ValueError(
            f"Correction must be based on current revision {current.revision}; "
            "export it with inspect before editing"
        )
    candidate.revision = current.revision + 1
    snapshot = RevisionSnapshot(
        reason=reason, dossier=corrected, created_at=datetime.now(timezone.utc)
    )
    _save_snapshot(workspace, snapshot)
    return snapshot


def record_decision(
    workspace: Path,
    scope: ReviewScope,
    target_id: str,
    action: ReviewAction,
    reviewer_id: str,
    rationale: str,
    revision: int,
    fingerprint: str,
) -> ScopedReviewDecision:
    """Require the revision and fingerprint shown by inspect; never edit snapshots."""
    dossier = get_snapshot(workspace).dossier
    if revision != dossier.candidate.revision:
        raise ValueError("The current revision changed; inspect it before deciding")
    inspected = inspect_item(dossier, scope, target_id)
    if fingerprint != inspected["fingerprint"]:
        raise ValueError("The reviewed fingerprint changed; inspect it before deciding")
    decision = ScopedReviewDecision(
        decision_id=uuid4().hex,
        candidate_id=dossier.candidate.candidate_id,
        candidate_revision=revision,
        scope=scope,
        target_id=target_id,
        fingerprint=fingerprint,
        action=action,
        reviewer_id=reviewer_id,
        notes=rationale,
        created_at=datetime.now(timezone.utc),
    )
    with (workspace / "decisions.jsonl").open(
        "a", encoding="utf-8", newline="\n"
    ) as stream:
        stream.write(decision.model_dump_json() + "\n")
    return decision


def effective_review_status(
    dossier: TraitDossier, decisions: list[ScopedReviewDecision]
) -> dict[str, Any]:
    """Latest matching decision wins; approval also needs approved dependencies."""
    dossier = validate_dossier(dossier)
    targets = review_targets(dossier)
    fingerprints = {key: inspect_item(dossier, *key)["fingerprint"] for key in targets}
    applicable: dict[ReviewKey, ScopedReviewDecision] = {}
    previous: set[ReviewKey] = set()
    for decision in decisions:
        if decision.candidate_id != dossier.candidate.candidate_id:
            raise ValueError("Decision belongs to another candidate")
        if decision.candidate_revision > dossier.candidate.revision:
            raise ValueError("Decision refers to a future revision")
        key = (decision.scope, decision.target_id)
        previous.add(key)
        if fingerprints.get(key) == decision.fingerprint:
            applicable[key] = decision

    states: dict[ReviewKey, dict[str, Any]] = {}
    for key in targets:
        _, dependencies, _ = _review_parts(dossier, *key)
        blocked_by = [
            f"{scope.value}:{target}"
            for scope, target in dependencies
            if not states.get((scope, target), {}).get("effective_approval", False)
        ]
        selected = applicable.get(key)
        if selected is None:
            state = "stale" if key in previous else "pending"
        elif selected.action == ReviewAction.REJECT:
            state = "rejected"
        elif selected.action == ReviewAction.REQUEST_CHANGES:
            state = "changes_requested"
        else:
            state = "blocked" if blocked_by else "approved"
        states[key] = {
            "scope": key[0].value,
            "target_id": key[1],
            "fingerprint": fingerprints[key],
            "state": state,
            "effective_approval": state == "approved",
            "decision": selected.model_dump(mode="json") if selected else None,
            "blocked_by": blocked_by,
        }

    history = []
    for decision in decisions:
        key = (decision.scope, decision.target_id)
        if fingerprints.get(key) != decision.fingerprint:
            state = "stale"
        elif applicable[key].decision_id != decision.decision_id:
            state = "superseded"
        else:
            state = "applicable"
        history.append({"state": state, **decision.model_dump(mode="json")})
    errors = validate_review_readiness(dossier)
    return {
        "candidate_id": dossier.candidate.candidate_id,
        "revision": dossier.candidate.revision,
        "ready_for_stage4": not errors
        and all(item["effective_approval"] for item in states.values()),
        "structural_errors": errors,
        "items": list(states.values()),
        "decisions": history,
    }


def workspace_status(workspace: Path) -> dict[str, Any]:
    snapshots, decisions = read_workspace(workspace)
    return effective_review_status(snapshots[-1].dossier, decisions)


def workspace_history(workspace: Path) -> dict[str, Any]:
    snapshots, decisions = read_workspace(workspace)
    return {
        "revisions": [
            {
                "revision": snapshot.dossier.candidate.revision,
                "reason": snapshot.reason,
                "created_at": snapshot.created_at.isoformat(),
            }
            for snapshot in snapshots
        ],
        "decisions": [decision.model_dump(mode="json") for decision in decisions],
    }
