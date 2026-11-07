"""Deterministic local integrity checks for curation records."""

from backend.models.curation import (
    EvidenceClaim,
    EvidenceSource,
    FindingSeverity,
    TraitCandidate,
    ValidationFinding,
)


def validate_candidate_references(
    candidate: TraitCandidate,
    claims: list[EvidenceClaim],
    sources: list[EvidenceSource],
) -> list[ValidationFinding]:
    """Check record references only; passing does not validate scientific content."""
    # Preserve the recovered diagnostic names and output shape for existing callers.
    evidence_ids = {claim.evidence_id for claim in claims}
    source_ids = {source.source_id for source in sources}
    findings: list[ValidationFinding] = []

    for evidence_id in candidate.evidence_ids:
        passed = evidence_id in evidence_ids
        findings.append(
            ValidationFinding(
                finding_id=f"{candidate.candidate_id}:claim:{evidence_id}",
                candidate_id=candidate.candidate_id,
                claim_id=evidence_id,
                check_name="candidate_claim_reference",
                severity=FindingSeverity.INFO if passed else FindingSeverity.ERROR,
                message=(
                    "Claim reference exists."
                    if passed
                    else f"Candidate references missing claim '{evidence_id}'."
                ),
                passed=passed,
            )
        )

    for claim in claims:
        for source_id in claim.source_ids:
            passed = source_id in source_ids
            findings.append(
                ValidationFinding(
                    finding_id=(
                        f"{candidate.candidate_id}:source:{claim.evidence_id}:{source_id}"
                    ),
                    candidate_id=candidate.candidate_id,
                    claim_id=claim.evidence_id,
                    check_name="claim_source_reference",
                    severity=FindingSeverity.INFO if passed else FindingSeverity.ERROR,
                    message=(
                        "Claim source reference exists."
                        if passed
                        else f"Claim references missing source '{source_id}'."
                    ),
                    passed=passed,
                )
            )

    for source_id in candidate.source_ids:
        passed = source_id in source_ids
        findings.append(
            ValidationFinding(
                finding_id=f"{candidate.candidate_id}:candidate-source:{source_id}",
                candidate_id=candidate.candidate_id,
                check_name="candidate_source_reference",
                severity=FindingSeverity.INFO if passed else FindingSeverity.ERROR,
                message=(
                    "Candidate source reference exists."
                    if passed
                    else f"Candidate references missing source '{source_id}'."
                ),
                passed=passed,
            )
        )

    return findings
