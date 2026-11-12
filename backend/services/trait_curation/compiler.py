"""Compile once, approve a manifest, then publish its exact bytes. Offline only."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, TypeAdapter

from backend.models.curation import (
    CurationModel,
    ExplanationText,
    Text,
    TraitDossier,
    require_unique_ids,
)
from backend.models.published_catalog import (
    PublishedClaim,
    PublishedEvidence,
    PublishedTrait,
    TraitCatalog,
)
from backend.services.trait_curation.preview import render_preview
from backend.services.trait_curation.validation import validate_dossier
from backend.services.trait_curation.verification import ExpectedCases, verify_cases
from backend.services.trait_curation.workflow import (
    RevisionSnapshot,
    ScopedReviewDecision,
    effective_review_status,
    inspect_item,
    read_workspace,
)

ROOT = Path(__file__).resolve().parents[3]
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ReleaseId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")]
PAYLOAD_FILES = {"catalog.json", "inputs.json", "preview.md", "verification.json"}
APPROVED_FILES = PAYLOAD_FILES | {"manifest.json", "approval.json"}


def stable_json(value: object) -> bytes:
    """UTF-8, LF, sorted object keys; list order is deliberately preserved."""
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SourceDocument(CurationModel):
    """Checksums recorded by acquisition, not independent document verification."""

    document_id: Text
    source_id: Text
    sha256: SHA256
    type: Literal["original", "excerpt"]
    url: Text
    version: Text | None = None


class FrozenInputs(CurationModel):
    snapshots: list[RevisionSnapshot] = Field(min_length=1)
    decisions: list[ScopedReviewDecision] = Field(min_length=1)
    expected_cases: ExpectedCases
    source_documents: list[SourceDocument]
    # Read legacy inputs without emitting their machine-local lookup path again.
    research_acquisition_path: str | None = Field(default=None, exclude=True)


class ReleaseManifest(CurationModel):
    release_id: ReleaseId
    catalog_schema_version: Literal["3.1"] = "3.1"
    compiler_version: Literal["stage4-v1"] = "stage4-v1"
    candidate_id: Text
    trait_id: Text
    revision: int = Field(ge=1, strict=True)
    dossier_sha256: SHA256
    case_set_id: Text
    files: dict[str, SHA256]


class ReleaseApproval(CurationModel):
    release_id: ReleaseId
    action: Literal["approve"]
    reviewer_id: Text
    rationale: Text
    created_at: AwareDatetime
    manifest_sha256: SHA256


def _approved_decisions(
    dossier: TraitDossier, decisions: list[ScopedReviewDecision]
) -> list[ScopedReviewDecision]:
    status = effective_review_status(dossier, decisions)
    if not status["ready_for_stage4"]:
        problems = status["structural_errors"] + [
            f"{item['scope']}:{item['target_id']} is {item['state']}"
            for item in status["items"]
            if not item["effective_approval"]
        ]
        raise ValueError("Stage 3 review is not ready: " + "; ".join(problems))
    return [
        ScopedReviewDecision.model_validate(item["decision"])
        for item in sorted(
            status["items"], key=lambda row: (row["scope"], row["target_id"])
        )
    ]


def compile_catalog(
    dossier: TraitDossier, decisions: list[ScopedReviewDecision]
) -> TraitCatalog:
    """Explicit projection after review checks; no legacy labels grant approval."""
    dossier = validate_dossier(dossier)
    _approved_decisions(dossier, decisions)
    evidence_ids = {ref for claim in dossier.claims for ref in claim.evidence_ids}
    evidence = [item for item in dossier.evidence if item.evidence_id in evidence_ids]
    source_ids = {ref for item in evidence for ref in item.source_ids}
    trait = PublishedTrait.model_validate(
        {
            "id": dossier.candidate.proposed_id,
            "name": dossier.candidate.proposed_name,
            "category": dossier.candidate.proposed_category,
            "description": dossier.candidate.description,
            "sources": [
                item.model_dump(mode="json")
                for item in dossier.sources
                if item.source_id in source_ids
            ],
            "evidence": [
                item.model_dump(
                    mode="json", include=set(PublishedEvidence.model_fields)
                )
                for item in evidence
            ],
            "claims": [
                item.model_dump(mode="json", include=set(PublishedClaim.model_fields))
                for item in dossier.claims
            ],
            "interpretation": (
                dossier.interpretation.model_dump(mode="json")
                if dossier.interpretation
                else None
            ),
            "explanations": [
                item.model_dump(mode="json", include=set(ExplanationText.model_fields))
                for item in dossier.explanations
            ],
        }
    )
    # Record lists and rule lists keep their validated input order. No filesystem
    # enumeration, clock, workspace paths or random IDs enter this projection.
    return TraitCatalog(schema_version="3.1", traits=[trait])


def source_documents(path: Path | None, source_ids: set[str]) -> list[SourceDocument]:
    if path is None:
        return []
    inventory = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(inventory, list) or any(
        not isinstance(row, dict) for row in inventory
    ):
        raise ValueError(
            "Acquisition inventory must be a JSON list of document records"
        )
    documents = [
        SourceDocument.model_validate(
            {key: row[key] for key in SourceDocument.model_fields if key in row}
        )
        for row in inventory
        if row.get("source_id") in source_ids
    ]
    require_unique_ids([item.document_id for item in documents], "document IDs")
    missing = source_ids - {item.source_id for item in documents}
    if missing:
        raise ValueError(
            f"Acquisition inventory missing published sources: {sorted(missing)}"
        )
    return sorted(documents, key=lambda item: item.document_id)


def build_candidate(
    workspace: Path,
    candidate: Path,
    release_id: str,
    cases_path: Path,
    acquisition_path: Path | None = None,
) -> ReleaseManifest:
    """Freeze the latest whole dossier. Failed cases leave no eligible candidate."""
    # Research uses this module's serialization helpers; import after module setup.
    from backend.services.trait_curation.research import verify_research_acquisition

    TypeAdapter(ReleaseId).validate_python(release_id)
    snapshots, history = read_workspace(workspace)
    selected = snapshots[-1]
    dossier = selected.dossier
    decisions = _approved_decisions(dossier, history)
    verified_documents = verify_research_acquisition(workspace, acquisition_path)
    catalog = compile_catalog(dossier, decisions)
    cases = ExpectedCases.model_validate_json(cases_path.read_bytes())
    verification = verify_cases(catalog.traits[0], cases)
    if not verification["passed"]:
        failed = [
            row["case_id"] for row in verification["cases"] if row["state"] == "failed"
        ]
        raise ValueError(f"Independent cases failed: {', '.join(failed)}")
    if acquisition_path is None:
        conventional = ROOT / "curation" / catalog.traits[0].id / "acquisition.json"
        if conventional.is_file():
            acquisition_path = conventional
    revisions = {decision.candidate_revision for decision in decisions}
    revisions.add(dossier.candidate.revision)
    inputs = FrozenInputs(
        snapshots=[
            snapshot
            for snapshot in snapshots
            if snapshot.dossier.candidate.revision in revisions
        ],
        decisions=decisions,
        expected_cases=cases,
        source_documents=(
            verified_documents
            if verified_documents is not None
            else source_documents(
                acquisition_path,
                {source.source_id for source in catalog.traits[0].sources},
            )
        ),
    )
    files = {
        "catalog.json": stable_json(catalog.model_dump(mode="json")),
        "inputs.json": stable_json(inputs.model_dump(mode="json")),
        "verification.json": stable_json(verification),
        "preview.md": render_preview(catalog, verification).encode("utf-8"),
    }
    manifest = ReleaseManifest(
        release_id=release_id,
        candidate_id=dossier.candidate.candidate_id,
        trait_id=dossier.candidate.proposed_id,
        revision=dossier.candidate.revision,
        dossier_sha256=sha256(stable_json(dossier.model_dump(mode="json"))),
        case_set_id=cases.case_set_id,
        files={name: sha256(data) for name, data in files.items()},
    )
    files["manifest.json"] = stable_json(manifest.model_dump(mode="json"))
    # Operational locator only: neither a manifest payload nor a published file.
    # Its target is untrusted until checked against reviewed/frozen provenance.
    if verified_documents is not None and acquisition_path is not None:
        files["acquisition-link.json"] = stable_json(
            {"research_acquisition_path": str(acquisition_path.resolve())}
        )
    candidate.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (candidate / name).open("xb") as stream:
            stream.write(data)
    return manifest


def _check_frozen_reviews(
    inputs: FrozenInputs, manifest: ReleaseManifest
) -> TraitDossier:
    revisions = {
        item.dossier.candidate.revision: item.dossier for item in inputs.snapshots
    }
    if len(revisions) != len(inputs.snapshots) or max(revisions) != manifest.revision:
        raise ValueError("Frozen snapshot revisions do not match the manifest")
    dossier = revisions[manifest.revision]
    if any(
        item.candidate.candidate_id != manifest.candidate_id
        or item.candidate.proposed_id != manifest.trait_id
        for item in revisions.values()
    ):
        raise ValueError("Frozen snapshots belong to another candidate or trait")
    if sha256(stable_json(dossier.model_dump(mode="json"))) != manifest.dossier_sha256:
        raise ValueError("Frozen dossier fingerprint does not match manifest")
    require_unique_ids([item.decision_id for item in inputs.decisions], "decision IDs")
    for decision in inputs.decisions:
        reviewed = revisions.get(decision.candidate_revision)
        if (
            reviewed is None
            or inspect_item(reviewed, decision.scope, decision.target_id)["fingerprint"]
            != decision.fingerprint
        ):
            raise ValueError("Frozen decision does not match its reviewed snapshot")
    if _approved_decisions(dossier, inputs.decisions) != inputs.decisions:
        raise ValueError("Frozen decisions must be the effective approved selection")
    return dossier


def _check_candidate_files(
    files: dict[str, bytes],
    require_approval: bool = False,
    *,
    check_compilation: bool,
) -> tuple[ReleaseManifest, FrozenInputs]:
    """Check frozen files; preview and approval also compare compilation output."""
    manifest = ReleaseManifest.model_validate_json(files["manifest.json"])
    if set(manifest.files) != PAYLOAD_FILES:
        raise ValueError("Manifest must identify all four candidate payload files")
    for name, digest in manifest.files.items():
        if sha256(files[name]) != digest:
            raise ValueError(f"Integrity check failed: {name}")
    catalog = TraitCatalog.model_validate_json(files["catalog.json"])
    inputs = FrozenInputs.model_validate_json(files["inputs.json"])
    dossier = _check_frozen_reviews(inputs, manifest)
    if check_compilation:
        # Before approval, compare expected bytes without replacing stored files.
        expected_catalog = compile_catalog(dossier, inputs.decisions)
        if (
            stable_json(expected_catalog.model_dump(mode="json"))
            != files["catalog.json"]
        ):
            raise ValueError("Catalog does not match the frozen reviewed dossier")
    if (
        catalog.traits[0].id != manifest.trait_id
        or inputs.expected_cases.case_set_id != manifest.case_set_id
    ):
        raise ValueError(
            "Manifest trait or case-set identity disagrees with frozen files"
        )
    # Recheck pure test results without replacing catalog or preview files.
    verification = verify_cases(catalog.traits[0], inputs.expected_cases)
    if not verification["passed"]:
        raise ValueError("Independent cases failed")
    if stable_json(verification) != files["verification.json"]:
        raise ValueError("Verification report does not match independent cases")
    if render_preview(catalog, verification).encode("utf-8") != files["preview.md"]:
        raise ValueError("Preview does not match the compiled catalog")
    if require_approval or "approval.json" in files:
        approval = ReleaseApproval.model_validate_json(files["approval.json"])
        if (
            approval.release_id != manifest.release_id
            or approval.manifest_sha256 != sha256(files["manifest.json"])
        ):
            raise ValueError("Release approval does not match the exact manifest")
    return manifest, inputs


def _read_candidate(path: Path, require_approval: bool = False) -> dict[str, bytes]:
    names = PAYLOAD_FILES | {"manifest.json"}
    if require_approval or (path / "approval.json").exists():
        names = names | {"approval.json"}
    return {name: (path / name).read_bytes() for name in sorted(names)}


def preview_candidate(candidate: Path) -> tuple[str, str]:
    files = _read_candidate(candidate)
    _check_candidate_files(files, check_compilation=True)
    return files["preview.md"].decode("utf-8"), sha256(files["manifest.json"])


def _check_current_selection(
    candidate: Path, workspace: Path, inputs: FrozenInputs, manifest: ReleaseManifest
) -> None:
    from backend.services.trait_curation.research import verify_research_acquisition

    snapshots, decisions = read_workspace(workspace)
    current = snapshots[-1].dossier
    if (
        current.candidate.revision != manifest.revision
        or sha256(stable_json(current.model_dump(mode="json")))
        != manifest.dossier_sha256
    ):
        raise ValueError("Review selection changed; build and approve a new candidate")
    if _approved_decisions(current, decisions) != inputs.decisions:
        raise ValueError("Required review decisions changed; build a new candidate")
    lookup_path = inputs.research_acquisition_path  # Legacy candidates only.
    link_path = candidate / "acquisition-link.json"
    if link_path.is_file():
        link = json.loads(link_path.read_bytes())
        lookup_path = (
            link.get("research_acquisition_path") if isinstance(link, dict) else None
        )
        if not isinstance(lookup_path, str) or not lookup_path.strip():
            raise ValueError("Candidate acquisition link must name an inventory path")
    inventory_path = (
        (candidate / lookup_path).resolve() if lookup_path is not None else None
    )
    verified_documents = verify_research_acquisition(workspace, inventory_path)
    if verified_documents is None:
        if inventory_path is not None or any(
            snapshot.dossier.candidate.pipeline_version.startswith("stage5-")
            or snapshot.dossier.candidate.research_run_sha256 is not None
            for snapshot in inputs.snapshots
        ):
            raise ValueError("Stage 5 candidate requires its research-origin workspace")
    elif verified_documents != inputs.source_documents:
        raise ValueError("Acquisition inventory changed since the displayed preview")


def approve_release(
    candidate: Path,
    workspace: Path,
    reviewer_id: str,
    rationale: str,
    manifest_fingerprint: str,
) -> ReleaseApproval:
    files = _read_candidate(candidate)
    manifest, inputs = _check_candidate_files(files, check_compilation=True)
    if sha256(files["manifest.json"]) != manifest_fingerprint:
        raise ValueError("Manifest fingerprint changed; preview before approving")
    _check_current_selection(candidate, workspace, inputs, manifest)
    approval = ReleaseApproval(
        release_id=manifest.release_id,
        action="approve",
        reviewer_id=reviewer_id,
        rationale=rationale,
        created_at=datetime.now(timezone.utc),
        manifest_sha256=manifest_fingerprint,
    )
    with (candidate / "approval.json").open("xb") as stream:
        stream.write(stable_json(approval.model_dump(mode="json")))
    return approval


def publish_candidate(candidate: Path, workspace: Path, releases: Path) -> Path:
    # Read once: a subsequent candidate edit cannot change the copied byte buffers.
    files = _read_candidate(candidate, require_approval=True)
    manifest, inputs = _check_candidate_files(
        files, require_approval=True, check_compilation=False
    )
    _check_current_selection(candidate, workspace, inputs, manifest)
    destination = releases / manifest.release_id
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (destination / name).open("xb") as stream:
            stream.write(data)
    # Detached checksum list covers the approval and manifest too, without a cycle.
    checksums = stable_json({name: sha256(data) for name, data in files.items()})
    with (destination / "checksums.json").open("xb") as stream:
        stream.write(checksums)
    verify_release(destination)
    return destination


def verify_release(release: Path) -> ReleaseManifest:
    if {path.name for path in release.iterdir()} != APPROVED_FILES | {"checksums.json"}:
        raise ValueError("Release has missing or unexpected files")
    files = _read_candidate(release, require_approval=True)
    expected = stable_json({name: sha256(data) for name, data in files.items()})
    if (release / "checksums.json").read_bytes() != expected:
        raise ValueError("Release integrity check failed (including checksums.json)")
    manifest, _ = _check_candidate_files(
        files, require_approval=True, check_compilation=False
    )
    return manifest
