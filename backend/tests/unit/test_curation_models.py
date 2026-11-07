from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel, ValidationError

from backend.main import app
from backend.models import (
    RsidCatalogItem,
    RsidDetail,
    SearchResponse,
    TraitAnalysisDetail,
    TraitAnalysisSummary,
    TraitCatalogDetail,
    TraitCatalogSummary,
)
from backend.models.curation import (
    CandidateStatus,
    ClaimStatus,
    ClaimType,
    EvidenceAssessment,
    EvidenceClaim,
    EvidenceLocation,
    EvidenceSource,
    ExtractionMethod,
    FindingSeverity,
    ReplicationStatus,
    ReviewAction,
    ReviewDecision,
    SourceType,
    TraitCandidate,
    ValidationFinding,
)
from backend.services.trait_curation.catalog import load_trait_catalog
from backend.services.trait_curation.validation import validate_candidate_references


def test_source_and_claim_require_location_but_allow_optional_metadata() -> None:
    source = EvidenceSource(
        source_id="src-1",
        source_type=SourceType.SCIENTIFIC_PUBLICATION,
        name="Example study",
        url="https://example.org/study",
        retrieved_at=datetime.now(timezone.utc),
    )
    claim = EvidenceClaim(
        evidence_id="claim-1",
        claim_type=ClaimType.TRAIT_ASSOCIATION,
        statement="A reported association.",
        source_ids=[source.source_id],
        source_location=EvidenceLocation(section="Synthetic results"),
        extraction_method=ExtractionMethod.MANUAL,
    )
    assert claim.extraction_confidence is None
    assert claim.source_location.section == "Synthetic results"
    assert claim.status == "pending"
    assert claim.validation_notes == []


def test_invalid_enum_ranges_and_identifiers_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceSource.model_validate(
            {"source_id": "s", "source_type": "made_up", "name": "Source"}
        )
    with pytest.raises(ValidationError):
        EvidenceClaim(
            evidence_id="c",
            claim_type=ClaimType.OTHER,
            statement="Claim",
            rsid="not-an-rsid",
            source_ids=["s"],
            source_location=EvidenceLocation(section="Synthetic results"),
            extraction_method=ExtractionMethod.MANUAL,
            extraction_confidence=1.1,
        )
    with pytest.raises(ValidationError):
        EvidenceAssessment(assessment_id="a", candidate_id="c", study_count=-1)
    with pytest.raises(ValidationError):
        EvidenceClaim(
            evidence_id="c",
            claim_type=ClaimType.OTHER,
            statement="Claim",
            source_ids=["s"],
            source_location=EvidenceLocation(section="Synthetic results"),
            extraction_method=ExtractionMethod.MANUAL,
            extracted_at=datetime(2024, 1, 1),
        )


def test_candidate_defaults_are_independent_and_review_is_revisioned() -> None:
    one = TraitCandidate(
        candidate_id="candidate-1", proposed_id="trait", proposed_name="Trait"
    )
    two = TraitCandidate(
        candidate_id="candidate-2", proposed_id="trait2", proposed_name="Trait 2"
    )
    one.keywords.append("test")
    assert two.keywords == []
    decision = ReviewDecision(
        decision_id="decision-1",
        candidate_id=one.candidate_id,
        candidate_revision=one.revision,
        action=ReviewAction.REQUEST_CHANGES,
        reviewer_id="local-reviewer",
        claim_ids_reviewed=["claim-1"],
    )
    assert decision.claim_ids_reviewed == ["claim-1"]


def test_reference_validation_detects_missing_source_and_claim() -> None:
    candidate = TraitCandidate(
        candidate_id="candidate-1",
        proposed_id="trait",
        proposed_name="Trait",
        evidence_ids=["missing-claim"],
    )
    claim = EvidenceClaim(
        evidence_id="claim-1",
        claim_type=ClaimType.VARIANT_EFFECT,
        statement="A claim",
        source_ids=["missing-source"],
        source_location=EvidenceLocation(section="Synthetic results"),
        extraction_method=ExtractionMethod.MANUAL,
    )
    findings = validate_candidate_references(candidate, [claim], [])
    assert {item.check_name for item in findings} == {
        "candidate_claim_reference",
        "claim_source_reference",
    }
    assert all(not item.passed and item.severity == "error" for item in findings)


def test_evidence_assessment_is_explicitly_versioned_and_separate() -> None:
    assessment = EvidenceAssessment(
        assessment_id="assessment-1",
        candidate_id="candidate-1",
        evidence_level="moderate",
        replication_status=ReplicationStatus.NOT_ESTABLISHED,
        rubric_version="evidence-rubric-v1",
        reviewed=True,
    )
    assert assessment.study_count is None
    assert assessment.rubric_version == "evidence-rubric-v1"


def test_existing_trait_catalog_still_validates() -> None:
    catalog = load_trait_catalog()
    assert len(catalog.traits) >= 5
    assert all(trait.rules for trait in catalog.traits)


def test_existing_api_route_paths_and_response_models_remain_declared() -> None:
    routes = {route.path: route for route in app.routes if isinstance(route, APIRoute)}
    expected = {
        "/traits/": ("GET", list[TraitCatalogSummary]),
        "/traits/{trait_id}": ("GET", TraitCatalogDetail),
        "/traits/{trait_id}/evaluate": ("POST", TraitAnalysisDetail),
        "/rsids/": ("GET", list[RsidCatalogItem]),
        "/rsids/{rsid}": ("GET", RsidDetail),
        "/search/": ("GET", SearchResponse),
        "/analyze/": ("POST", list[TraitAnalysisSummary]),
    }
    for path, (method, response_model) in expected.items():
        assert routes[path].methods == {method}
        assert routes[path].response_model == response_model
    assert "/traits/{trait_id}/detail" not in routes
    assert (
        not {"EvidenceSource", "EvidenceClaim", "TraitCandidate", "ReviewDecision"}
        & app.openapi()["components"]["schemas"].keys()
    )


def test_source_location_and_extraction_provenance_round_trip() -> None:
    location = EvidenceLocation(
        section="Results", page="3", paragraph=2, table="1", figure="2a"
    )
    claim = EvidenceClaim(
        evidence_id="claim-1",
        claim_type=ClaimType.VARIANT_EFFECT,
        statement="A source-reported statement awaiting review.",
        rsid="rs671",
        source_ids=["source-1"],
        source_location=location,
        source_passage="Synthetic test passage.",
        extraction_method=ExtractionMethod.RULE_BASED,
        extractor_version="test-v1",
        extraction_confidence=0.5,
    )
    restored = EvidenceClaim.model_validate_json(claim.model_dump_json())
    assert restored == claim
    assert restored.source_location == location
    assert restored.status is ClaimStatus.PENDING
    with pytest.raises(ValidationError):
        EvidenceLocation(paragraph=0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "relative/path"),
        ("url", "ftp://example.org/study"),
        ("url", "https://example.org/a b"),
        ("pmid", "PMID123"),
        ("pmcid", "123"),
        ("publication_year", 1499),
    ],
)
def test_source_rejects_invalid_bibliographic_fields(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        EvidenceSource.model_validate(
            {"source_id": "s", "source_type": "other", "name": "Source", field: value}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rsid", "not-an-rsid"),
        ("extraction_confidence", -0.1),
        ("extraction_confidence", 1.1),
        ("source_ids", []),
        ("claim_type", "unknown"),
        ("extraction_method", "unknown"),
    ],
)
def test_claim_rejects_invalid_fields_independently(field: str, value: object) -> None:
    payload = {
        "claim_id": "c",
        "claim_type": "other",
        "statement": "Claim",
        "source_ids": ["s"],
        "source_location": {"section": "Synthetic results"},
        "extraction_method": "manual",
        field: value,
    }
    with pytest.raises(ValidationError):
        EvidenceClaim.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload", "field"),
    [
        (
            EvidenceSource,
            {"source_id": "s", "source_type": "other", "name": "Source"},
            "retrieved_at",
        ),
        (
            EvidenceClaim,
            {
                "claim_id": "c",
                "claim_type": "other",
                "statement": "Claim",
                "source_ids": ["s"],
                "source_location": {"section": "Synthetic results"},
                "extraction_method": "manual",
            },
            "extracted_at",
        ),
        (
            TraitCandidate,
            {"candidate_id": "c", "proposed_id": "trait", "proposed_name": "Trait"},
            "created_at",
        ),
        (
            ValidationFinding,
            {
                "finding_id": "f",
                "candidate_id": "c",
                "check_name": "reference",
                "severity": "info",
                "message": "Exists",
                "passed": True,
            },
            "created_at",
        ),
        (
            EvidenceAssessment,
            {"assessment_id": "a", "candidate_id": "c"},
            "assessed_at",
        ),
        (
            ReviewDecision,
            {
                "decision_id": "d",
                "candidate_id": "c",
                "candidate_revision": 1,
                "action": "request_changes",
                "reviewer_id": "r",
            },
            "created_at",
        ),
    ],
)
def test_all_record_timestamps_require_timezone(
    model: type[BaseModel], payload: dict[str, object], field: str
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({**payload, field: datetime(2024, 1, 1)})
    aware = datetime(2024, 1, 1, tzinfo=timezone(timedelta(hours=2)))
    assert getattr(model.model_validate({**payload, field: aware}), field) == aware


def test_reference_validation_covers_all_reference_kinds_and_mixed_results() -> None:
    source = EvidenceSource(source_id="s", source_type=SourceType.OTHER, name="Source")
    claim = EvidenceClaim(
        evidence_id="claim",
        claim_type=ClaimType.OTHER,
        statement="Claim",
        source_ids=["s"],
        source_location=EvidenceLocation(section="Synthetic results"),
        extraction_method=ExtractionMethod.MANUAL,
    )
    candidate = TraitCandidate(
        candidate_id="candidate",
        proposed_id="trait",
        proposed_name="Trait",
        evidence_ids=["claim"],
        source_ids=["s"],
    )
    findings = validate_candidate_references(candidate, [claim], [source])
    assert {item.check_name for item in findings} == {
        "candidate_claim_reference",
        "claim_source_reference",
        "candidate_source_reference",
    }
    assert len(findings) == 3
    assert all(
        item.passed and item.severity is FindingSeverity.INFO for item in findings
    )
    assert all(item.candidate_id == candidate.candidate_id for item in findings)
    assert len({item.finding_id for item in findings}) == len(findings)

    candidate.source_ids.append("missing")
    mixed = validate_candidate_references(candidate, [claim], [source])
    assert sum(item.passed for item in mixed) == 3
    failed = [item for item in mixed if not item.passed]
    assert len(failed) == 1
    assert failed[0].check_name == "candidate_source_reference"
    assert failed[0].severity is FindingSeverity.ERROR
    assert failed[0].claim_id is None
    assert "missing" in failed[0].message


def test_reference_checks_do_not_promote_authoring_records() -> None:
    candidate = TraitCandidate(
        candidate_id="c", proposed_id="trait", proposed_name="Trait"
    )
    assessment = EvidenceAssessment(assessment_id="a", candidate_id="c")
    # An empty dossier has no references to check; this is not scientific approval.
    assert validate_candidate_references(candidate, [], []) == []
    assert candidate.status is CandidateStatus.DRAFT
    assert assessment.replication_status is ReplicationStatus.NOT_ASSESSED
    assert assessment.evidence_level is None
    assert assessment.reviewed is False


def test_review_decision_preserves_revision_and_action_without_mutation() -> None:
    candidate = TraitCandidate(
        candidate_id="c", revision=2, proposed_id="trait", proposed_name="Trait"
    )
    decision = ReviewDecision(
        decision_id="d",
        candidate_id="c",
        candidate_revision=2,
        action=ReviewAction.APPROVE,
        reviewer_id="test-reviewer",
        notes="Synthetic record",
    )
    assert ReviewDecision.model_validate_json(decision.model_dump_json()) == decision
    assert candidate.status is CandidateStatus.DRAFT
    with pytest.raises(ValidationError):
        ReviewDecision.model_validate(
            {**decision.model_dump(), "candidate_revision": 0}
        )
