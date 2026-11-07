"""Stage 2 contracts: model rules, dossier integrity and publication safeguards."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from backend.models import TraitCatalog as LegacyTraitCatalog
from backend.models.curation import (
    AssessedClaim,
    EvidenceClaim,
    ExplanationContent,
    TraitCandidate,
    TraitDossier,
)
from backend.models.interpretation import (
    AlleleCountInterpretation,
    AlleleCountRule,
    EducationalInterpretation,
    VariantPlacement,
    VariantRequirements,
)
from backend.models.published_catalog import TraitCatalog

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def reviewed_catalog() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (ROOT / "curation/examples/synthetic-reviewed-catalog.json").read_text(
            encoding="utf-8"
        )
    )
    return data


@pytest.fixture
def allele_count_data() -> dict[str, Any]:
    return {
        "strategy": "allele_count",
        "claim_ids": ["synthetic-reviewed-claim"],
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


@pytest.fixture
def result_catalog(
    reviewed_catalog: dict[str, Any], allele_count_data: dict[str, Any]
) -> dict[str, Any]:
    trait = reviewed_catalog["traits"][0]
    trait["interpretation"] = allele_count_data
    trait["evidence"][0]["statement"] = "A fictional study describes an A/G marker."
    trait["claims"][0]["statement"] = "A copies do not predict personal symptoms."
    trait["explanations"][0]["body"] = "This synthetic example describes allele copies."
    trait["explanations"].extend(
        {
            "content_id": f"result-{key}",
            "kind": "outcome_summary",
            "body": f"Synthetic explanation for {key}.",
            "claim_ids": ["synthetic-reviewed-claim"],
            "result_key": key,
            "reviewed": True,
        }
        for key in ("0", "1", "2", "unavailable")
    )
    return reviewed_catalog


def test_educational_catalog_traceability(reviewed_catalog: dict[str, Any]) -> None:
    catalog = TraitCatalog.model_validate(reviewed_catalog)
    trait = catalog.traits[0]
    assert trait.candidate.status == trait.claims[0].status == "approved"
    assert trait.evidence[0].status == "pending"
    assert trait.claims[0].evidence_ids == [trait.evidence[0].evidence_id]
    assert trait.evidence[0].source_ids == [trait.sources[0].source_id]
    assert trait.explanations[0].claim_ids == [trait.claims[0].claim_id]
    assert trait.explanations[0].reviewed is True
    assert isinstance(trait.interpretation, EducationalInterpretation)
    assert set(trait.interpretation.model_dump()) == {"strategy", "claim_ids"}
    assert TraitCatalog.model_validate_json(catalog.model_dump_json()) == catalog


def test_rs671_remains_score_free_and_unapproved() -> None:
    dossier = TraitDossier.model_validate_json(
        (ROOT / "curation/alcohol_flush/stage2-draft.json").read_text(encoding="utf-8")
    )
    model = dossier.interpretation
    assert isinstance(model, AlleleCountInterpretation)
    assert [(rule.genotype, rule.copies) for rule in model.rules] == [
        ("GG", 0),
        ("AG", 1),
        ("AA", 2),
    ]
    assert {placement.genome_build for placement in model.requirements.placements} == {
        "GRCh37",
        "GRCh38",
    }
    assert dossier.candidate.status == "draft"
    assert all(
        claim.status == "pending" and claim.assessment is None
        for claim in dossier.claims
    )
    assert all(finding.status == "pending" for finding in dossier.evidence)
    assert all(not text.reviewed for text in dossier.explanations)
    assert '"score"' not in dossier.model_dump_json()
    assert TraitDossier.model_validate_json(dossier.model_dump_json()) == dossier
    with pytest.raises(ValidationError, match="candidates must be approved"):
        TraitCatalog.model_validate({"schema_version": "3.0", "traits": [dossier]})


def test_draft_can_grow_without_finished_content(
    reviewed_catalog: dict[str, Any],
) -> None:
    trait = reviewed_catalog["traits"][0]
    candidate = {**trait["candidate"], "status": "draft"}
    draft = TraitDossier(candidate=TraitCandidate.model_validate(candidate))
    assert draft.sources == draft.evidence == draft.claims == draft.explanations == []
    assert draft.interpretation is None
    data = {
        "candidate": candidate,
        "sources": trait["sources"],
        "evidence": trait["evidence"],
    }
    assert TraitDossier.model_validate(data).claims == []
    data["claims"] = [{**trait["claims"][0], "status": "pending", "assessment": None}]
    draft = TraitDossier.model_validate(data)
    assert draft.claims[0].status == "pending"
    assert draft.interpretation is None and not draft.explanations
    assert TraitDossier.model_validate_json(draft.model_dump_json()) == draft


@pytest.mark.parametrize("section", ["catalog", "candidate"])
def test_catalog_rejects_unknown_fields(
    reviewed_catalog: dict[str, Any], section: str
) -> None:
    target = (
        reviewed_catalog
        if section == "catalog"
        else reviewed_catalog["traits"][0]["candidate"]
    )
    target["unexpected"] = "must not be discarded"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("candidate", "source_ids"),
        ("candidate", "evidence_ids"),
        ("evidence", "source_ids"),
        ("claims", "evidence_ids"),
        ("interpretation", "claim_ids"),
        ("explanations", "claim_ids"),
    ],
)
def test_draft_references_resolve_with_optional_interpretation(
    reviewed_catalog: dict[str, Any], section: str, field: str
) -> None:
    data = reviewed_catalog["traits"][0]
    if section != "interpretation":
        data["interpretation"] = None
    target = data[section]
    if isinstance(target, list):
        target = target[0]
    # A source finding cannot substitute for an assessed claim in an explanation.
    target[field] = ["synthetic-finding" if section == "explanations" else "missing"]
    with pytest.raises(ValidationError, match="reference missing IDs"):
        TraitDossier.model_validate(data)


def test_empty_claims_do_not_bypass_references(
    reviewed_catalog: dict[str, Any],
) -> None:
    data = reviewed_catalog["traits"][0]
    data.update(claims=[], interpretation=None)
    with pytest.raises(ValidationError, match="content claims reference missing"):
        TraitDossier.model_validate(data)


@pytest.mark.parametrize("section", ["sources", "evidence", "claims", "explanations"])
def test_dossier_ids_are_unique(reviewed_catalog: dict[str, Any], section: str) -> None:
    data = reviewed_catalog["traits"][0]
    data[section].append(deepcopy(data[section][0]))
    with pytest.raises(ValidationError, match="must be unique"):
        TraitDossier.model_validate(data)


@pytest.mark.parametrize("section", ["evidence", "assessment"])
def test_records_belong_to_their_dossier(
    reviewed_catalog: dict[str, Any], section: str
) -> None:
    data = reviewed_catalog["traits"][0]
    if section == "evidence":
        data["evidence"][0]["trait_id"] = "another_trait"
    else:
        data["claims"][0]["assessment"]["candidate_id"] = "another_candidate"
    with pytest.raises(ValidationError, match="must match the dossier"):
        TraitDossier.model_validate(data)


def test_catalog_trait_ids_are_unique(reviewed_catalog: dict[str, Any]) -> None:
    reviewed_catalog["traits"].append(deepcopy(reviewed_catalog["traits"][0]))
    with pytest.raises(ValidationError, match="trait IDs must be unique"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize("version", ["2.0", "3.1", None])
def test_catalog_requires_its_schema_version(
    reviewed_catalog: dict[str, Any], version: str | None
) -> None:
    if version is None:
        del reviewed_catalog["schema_version"]
    else:
        reviewed_catalog["schema_version"] = version
    with pytest.raises(ValidationError, match="schema_version"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize(
    "field", ["requirements", "counted_allele", "rules", "unavailable_policy"]
)
def test_allele_count_requires_strategy_fields(
    allele_count_data: dict[str, Any], field: str
) -> None:
    del allele_count_data[field]
    with pytest.raises(ValidationError, match=field):
        AlleleCountInterpretation.model_validate(allele_count_data)


@pytest.mark.parametrize("field", ["requirements", "rules"])
def test_education_rejects_genotype_fields(field: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EducationalInterpretation.model_validate(
            {"strategy": "educational", "claim_ids": ["claim"], field: []}
        )


def test_unknown_strategies_are_rejected(reviewed_catalog: dict[str, Any]) -> None:
    data = reviewed_catalog["traits"][0]
    data["interpretation"]["strategy"] = "weighted_score"
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        TraitDossier.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ploidy", 1),
        ("orientation", "reverse"),
        ("coordinate_system", "0-based"),
        ("alleles", ["A", "A"]),
        ("alleles", ["A", "N"]),
        ("alleles", ["A", "C", "G"]),
        ("placements", []),
        ("unexpected", True),
    ],
)
def test_variant_requirements_reject_invalid_fields(
    allele_count_data: dict[str, Any], field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        VariantRequirements.model_validate(
            {**allele_count_data["requirements"], field: value}
        )


def test_representation_fields_are_required(allele_count_data: dict[str, Any]) -> None:
    requirements = allele_count_data["requirements"]
    for field in (
        "rsid",
        "placements",
        "orientation",
        "coordinate_system",
        "ploidy",
        "alleles",
    ):
        incomplete = requirements.copy()
        del incomplete[field]
        with pytest.raises(ValidationError, match=field):
            VariantRequirements.model_validate(incomplete)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("genome_build", "unknown"),
        ("chromosome", "X"),
        ("position", 0),
        ("sequence_accession", "NC_000001"),
    ],
)
def test_placements_require_valid_coordinates(
    allele_count_data: dict[str, Any], field: str, value: object
) -> None:
    placement = allele_count_data["requirements"]["placements"][0]
    with pytest.raises(ValidationError, match=field):
        VariantPlacement.model_validate({**placement, field: value})


def test_each_build_has_one_placement(allele_count_data: dict[str, Any]) -> None:
    requirements = allele_count_data["requirements"]
    requirements["placements"].append(
        {**requirements["placements"][0], "position": 102}
    )
    with pytest.raises(ValidationError, match="one placement per genome build"):
        VariantRequirements.model_validate(requirements)


def test_rule_genotypes_normalize_case_and_order() -> None:
    rule = AlleleCountRule(genotype="ga", copies=1)
    assert rule.genotype == "AG" and rule.copies == 1


@pytest.mark.parametrize("genotype", ["AA?", "A/G", "G/.", "A", "NN"])
def test_rule_genotypes_reject_malformed_calls(genotype: str) -> None:
    with pytest.raises(ValidationError, match="exactly two SNV alleles"):
        AlleleCountRule(genotype=genotype, copies=1)


@pytest.mark.parametrize("copies", [1, 2])
def test_normalized_rules_cannot_overlap(
    allele_count_data: dict[str, Any], copies: int
) -> None:
    allele_count_data["rules"].append({"genotype": "ga", "copies": copies})
    with pytest.raises(ValidationError, match="normalized genotype rules overlap"):
        AlleleCountInterpretation.model_validate(allele_count_data)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"counted_allele": "C"}, "counted allele must be supported"),
        ({"rules": [{"genotype": "AC", "copies": 1}]}, "incompatible alleles"),
        ({"rules": [{"genotype": "AG", "copies": 2}]}, "copies must match"),
    ],
)
def test_rules_match_alleles_and_copy_counts(
    allele_count_data: dict[str, Any], change: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        AlleleCountInterpretation.model_validate({**allele_count_data, **change})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_ids", []),
        ("source_ids", ["source-1", "source-2"]),
        ("source_location", None),
        ("source_location", {}),
        ("source_location", {"locator": " "}),
    ],
)
def test_findings_require_one_source_and_a_locator(
    reviewed_catalog: dict[str, Any], field: str, value: object
) -> None:
    finding = reviewed_catalog["traits"][0]["evidence"][0]
    with pytest.raises(ValidationError):
        EvidenceClaim.model_validate({**finding, field: value})


def test_finding_cannot_omit_its_location(reviewed_catalog: dict[str, Any]) -> None:
    finding = reviewed_catalog["traits"][0]["evidence"][0]
    del finding["source_location"]
    with pytest.raises(ValidationError, match="source_location"):
        EvidenceClaim.model_validate(finding)


def test_claims_combine_findings_with_separate_locations(
    reviewed_catalog: dict[str, Any],
) -> None:
    data = reviewed_catalog["traits"][0]
    data["sources"].append({**data["sources"][0], "source_id": "second-source"})
    data["evidence"].append(
        {
            **data["evidence"][0],
            "evidence_id": "second-finding",
            "source_ids": ["second-source"],
            "source_location": {"table": "2"},
        }
    )
    data["claims"][0]["evidence_ids"].append("second-finding")
    trait = TraitDossier.model_validate(data)
    assert trait.evidence[1].source_ids == ["second-source"]
    assert trait.evidence[1].source_location.table == "2"
    assert len(trait.claims[0].evidence_ids) == 2


def test_recovered_names_load_but_ambiguous_names_fail(
    reviewed_catalog: dict[str, Any],
) -> None:
    data = reviewed_catalog["traits"][0]
    data["candidate"]["claim_ids"] = ["synthetic-finding"]
    finding = data["evidence"][0]
    finding["claim_id"] = finding.pop("evidence_id")
    draft = TraitDossier.model_validate(data)
    payload = draft.model_dump()
    assert payload["candidate"]["evidence_ids"] == [draft.evidence[0].evidence_id]
    assert "claim_ids" not in payload["candidate"]
    assert "claim_id" not in payload["evidence"][0]
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TraitCandidate.model_validate({**data["candidate"], "evidence_ids": ["new"]})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvidenceClaim.model_validate({**finding, "evidence_id": "new"})


@pytest.mark.parametrize("change", ["missing", "unreviewed", "no_rationale"])
def test_claim_approval_requires_a_reviewed_rationale(
    reviewed_catalog: dict[str, Any], change: str
) -> None:
    claim = reviewed_catalog["traits"][0]["claims"][0]
    if change == "missing":
        del claim["assessment"]
    elif change == "unreviewed":
        claim["assessment"]["reviewed"] = False
    else:
        del claim["assessment"]["assessment_rationale"]
    with pytest.raises(ValidationError, match="reviewed rationale"):
        AssessedClaim.model_validate(claim)


def test_explanation_kinds_cover_application_text() -> None:
    legacy = json.loads((ROOT / "data/traits.json").read_text(encoding="utf-8"))
    metadata = {
        "id",
        "name",
        "category",
        "evidence_level",
        "keywords",
        "sources",
        "rules",
        "result_content",
    }
    general_kinds: set[str] = set()
    result_kinds: set[str] = set()
    for trait in legacy["traits"]:
        general_kinds.update(set(trait) - metadata)
        for result_content in trait["result_content"].values():
            result_kinds.update(result_content)
    for kind in sorted(general_kinds | result_kinds):
        data = {
            "content_id": "text",
            "kind": kind,
            "body": "Synthetic explanation.",
            "claim_ids": ["claim"],
        }
        if kind in result_kinds:
            with pytest.raises(ValidationError, match="result_key"):
                ExplanationContent.model_validate(data)
            data["result_key"] = "1"
        content = ExplanationContent.model_validate(data)
        assert content.title is None and content.reviewed is False


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "unknown"},
        {"result_key": "1"},
        {"claim_ids": []},
        {"title": " "},
        {"body": " "},
    ],
)
def test_explanations_reject_invalid_content(
    reviewed_catalog: dict[str, Any], change: dict[str, Any]
) -> None:
    content = reviewed_catalog["traits"][0]["explanations"][0]
    with pytest.raises(ValidationError):
        ExplanationContent.model_validate({**content, **change})


@pytest.mark.parametrize("field", ["claims", "interpretation", "explanations"])
def test_publication_requires_complete_dossiers(
    reviewed_catalog: dict[str, Any], field: str
) -> None:
    data = reviewed_catalog["traits"][0]
    del data[field]
    if field == "claims":
        del data["interpretation"], data["explanations"]
    TraitDossier.model_validate(data)
    with pytest.raises(ValidationError, match="published entries require"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize(
    "status", [None, "draft", "retrieved", "validating", "needs_review", "rejected"]
)
def test_publication_requires_candidate_approval(
    reviewed_catalog: dict[str, Any], status: str | None
) -> None:
    data = reviewed_catalog["traits"][0]
    if status is None:
        del data["candidate"]["status"]
    else:
        data["candidate"]["status"] = status
    assert TraitDossier.model_validate(data).candidate.status == (status or "draft")
    with pytest.raises(ValidationError, match="candidates must be approved"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("claims", "status", "pending"),
        ("claims", "status", "rejected"),
        ("explanations", "reviewed", False),
    ],
)
def test_candidate_approval_does_not_replace_other_reviews(
    reviewed_catalog: dict[str, Any], section: str, field: str, value: object
) -> None:
    data = reviewed_catalog["traits"][0]
    data["evidence"][0]["status"] = "validated"
    data[section][0][field] = value
    TraitDossier.model_validate(data)
    with pytest.raises(ValidationError, match="must be approved|must be reviewed"):
        TraitCatalog.model_validate(reviewed_catalog)


@pytest.mark.parametrize("status", ["rejected", "needs_review"])
def test_flagged_evidence_blocks_publication(
    reviewed_catalog: dict[str, Any], status: str
) -> None:
    data = reviewed_catalog["traits"][0]
    data["evidence"][0]["status"] = status
    TraitDossier.model_validate(data)
    with pytest.raises(
        ValidationError, match="evidence cannot be rejected or need review"
    ):
        TraitCatalog.model_validate(reviewed_catalog)


def test_unused_rejected_evidence_also_blocks_publication(
    reviewed_catalog: dict[str, Any],
) -> None:
    data = reviewed_catalog["traits"][0]
    data["evidence"].append(
        {**data["evidence"][0], "evidence_id": "unused", "status": "rejected"}
    )
    with pytest.raises(ValidationError, match="evidence cannot be rejected"):
        TraitCatalog.model_validate(reviewed_catalog)


def test_education_cannot_publish_result_text(reviewed_catalog: dict[str, Any]) -> None:
    reviewed_catalog["traits"][0]["explanations"][0].update(
        kind="outcome_summary", result_key="1"
    )
    with pytest.raises(ValidationError, match="educational entries cannot have result"):
        TraitCatalog.model_validate(reviewed_catalog)


def test_valid_allele_count_catalog(result_catalog: dict[str, Any]) -> None:
    catalog = TraitCatalog.model_validate(result_catalog)
    assert {content.result_key for content in catalog.traits[0].explanations} == {
        None,
        "0",
        "1",
        "2",
        "unavailable",
    }
    assert TraitCatalog.model_validate_json(catalog.model_dump_json()) == catalog


@pytest.mark.parametrize("key", ["likely", "3", "01"])
def test_result_keys_match_supported_outputs(
    result_catalog: dict[str, Any], key: str
) -> None:
    result_catalog["traits"][0]["explanations"][1]["result_key"] = key
    with pytest.raises(ValidationError, match="result_key must match"):
        TraitCatalog.model_validate(result_catalog)


def test_result_keys_follow_actual_table_outputs(
    result_catalog: dict[str, Any],
) -> None:
    result_catalog["traits"][0]["interpretation"]["rules"].pop()
    with pytest.raises(ValidationError, match="result_key must match"):
        TraitCatalog.model_validate(result_catalog)


def test_result_slots_allow_different_kinds_but_not_duplicates(
    result_catalog: dict[str, Any],
) -> None:
    content = result_catalog["traits"][0]["explanations"]
    content.append({**content[1], "content_id": "another-summary"})
    with pytest.raises(ValidationError, match="kind and result_key must be unique"):
        TraitCatalog.model_validate(result_catalog)
    content[-1]["kind"] = "headline"
    TraitCatalog.model_validate(result_catalog)


def test_result_text_cites_interpretation_claims(
    result_catalog: dict[str, Any],
) -> None:
    data = result_catalog["traits"][0]
    context = deepcopy(data["claims"][0])
    context["claim_id"] = "context-claim"
    context["assessment"]["assessment_id"] = "context-assessment"
    data["claims"].append(context)
    data["explanations"][0]["claim_ids"] = ["context-claim"]
    result_text = data["explanations"][1]
    result_text["claim_ids"] = ["context-claim"]
    with pytest.raises(ValidationError, match="reference an interpretation claim"):
        TraitCatalog.model_validate(result_catalog)
    result_text["claim_ids"].append("synthetic-reviewed-claim")
    TraitCatalog.model_validate(result_catalog)


def test_v2_and_stage2_catalogs_are_separate(reviewed_catalog: dict[str, Any]) -> None:
    legacy = json.loads((ROOT / "data/traits.json").read_text(encoding="utf-8"))
    assert LegacyTraitCatalog.model_validate(legacy).version == "2.0"
    with pytest.raises(ValidationError):
        TraitCatalog.model_validate(legacy)
    with pytest.raises(ValidationError):
        LegacyTraitCatalog.model_validate(reviewed_catalog)
