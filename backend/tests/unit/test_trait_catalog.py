import pytest

from backend.models import (
    CuratedTraitRule,
    GenotypeInterpretation,
    TraitDefinition,
    Variant,
)
from backend.services.trait_curation.catalog import (
    _find_interpretation,
    _normalize_genotype,
    build_trait_detail,
    build_trait_result,
    evaluate_trait,
    list_trait_definitions,
)


def to_alleles(genotype: str | None) -> list[str] | None:
    if genotype is None:
        return None
    return [allele for allele in genotype if allele not in {"/", " "}]


@pytest.fixture
def simple_trait() -> TraitDefinition:
    return TraitDefinition(
        id="test_trait",
        name="Test Trait",
        category="health",
        description="desc",
        simple_summary="simple",
        technical_summary="tech",
        evidence_level="strong",
        keywords=[],
        sources=[],
        rules=[
            CuratedTraitRule(
                rsid="rs1",
                genotype_meanings=[
                    GenotypeInterpretation(
                        genotype=["AA"],
                        meaning="positive",
                        effect="good",
                        score=0.5,
                    ),
                    GenotypeInterpretation(
                        genotype=["GG"],
                        meaning="negative",
                        effect="bad",
                        score=-0.5,
                    ),
                ],
                weight=1.0,
                priority=1,
                description="rule desc",
                gene="GENE1",
            )
        ],
    )


@pytest.fixture
def matching_variant() -> list[Variant]:
    return [Variant(rsid="rs1", chromosome="1", position=1, genotype=["A", "A"])]


@pytest.fixture
def non_matching_variant() -> list[Variant]:
    return [Variant(rsid="rs1", chromosome="1", position=1, genotype=["T", "T"])]


@pytest.fixture
def missing_variant() -> list[Variant]:
    return []


# --- Test normalization ---


def test_normalize_genotype_orders_letters() -> None:
    assert _normalize_genotype("GA") == "AG"


def test_normalize_genotype_removes_slash() -> None:
    assert _normalize_genotype("A/G") == "AG"


def test_normalize_genotype_uppercase() -> None:
    assert _normalize_genotype("ag") == "AG"


# --- Test interpretation matching ---


def test_find_interpretation_match(simple_trait: TraitDefinition) -> None:
    rule = simple_trait.rules[0]
    result = _find_interpretation(rule, "AA")
    assert result is not None
    assert result.meaning == "positive"


def test_find_interpretation_no_match(simple_trait: TraitDefinition) -> None:
    rule = simple_trait.rules[0]
    result = _find_interpretation(rule, "TT")
    assert result is None


# --- Test trait evaluation ---


def test_evaluate_trait_match(
    simple_trait: TraitDefinition, matching_variant: list[Variant]
) -> None:
    evaluation = evaluate_trait(simple_trait, matching_variant)

    assert evaluation.result == "likely"
    assert evaluation.score > 0
    assert evaluation.coverage == 1.0
    assert len(evaluation.matched_rules) == 1


def test_evaluate_trait_no_match(
    simple_trait: TraitDefinition, non_matching_variant: list[Variant]
) -> None:
    evaluation = evaluate_trait(simple_trait, non_matching_variant)

    assert evaluation.result == "inconclusive"
    assert evaluation.score == 0
    assert len(evaluation.matched_rules) == 0


def test_evaluate_trait_missing(
    simple_trait: TraitDefinition, missing_variant: list[Variant]
) -> None:
    evaluation = evaluate_trait(simple_trait, missing_variant)

    assert evaluation.coverage == 0.0
    assert evaluation.confidence == 0.0
    assert evaluation.result == "inconclusive"
    assert evaluation.missing_rsids == ["rs1"]


#  --- Test confidence behaviour ---


def test_confidence_reduced_by_missing_data(simple_trait: TraitDefinition) -> None:
    partial_variants = [Variant(rsid="rs1", chromosome="1", position=1, genotype=None)]

    evaluation = evaluate_trait(simple_trait, partial_variants)

    assert evaluation.coverage == 0.0
    assert evaluation.confidence == 0.0


# --- Test result building ---


def test_build_trait_result(
    simple_trait: TraitDefinition, matching_variant: list[Variant]
) -> None:
    evaluation = evaluate_trait(simple_trait, matching_variant)
    result = build_trait_result(evaluation)

    assert result.trait_id == "test_trait"
    assert result.result == "likely"
    assert result.confidence > 0
    assert result.description == "desc"
    assert result.matched_rsids == ["rs1"]
    assert result.observed_rsids == ["rs1"]
    assert result.coverage == 1.0
    assert result.simple_summary == "simple"
    assert "Test Trait" in result.user_summary
    assert "coverage" in result.explanation_preview.lower()
    assert result.result_badge_tooltip


# --- Test detail building ---


def test_trait_detail_matched(
    simple_trait: TraitDefinition, matching_variant: list[Variant]
) -> None:
    detail = build_trait_detail(simple_trait, matching_variant)

    rsid = detail.rsids[0]

    assert rsid.status == "matched"
    assert rsid.meaning == "positive"
    assert rsid.effect == "good"
    assert rsid.user_genotype == ["A", "A"]
    assert rsid.contribution == "raises"
    assert "matched" in rsid.status_explanation.lower()


def test_trait_detail_no_match(
    simple_trait: TraitDefinition, non_matching_variant: list[Variant]
) -> None:
    detail = build_trait_detail(simple_trait, non_matching_variant)

    rsid = detail.rsids[0]

    assert rsid.status == "no_match"
    assert rsid.meaning is not None
    assert rsid.contribution == "unknown"


def test_trait_detail_missing(
    simple_trait: TraitDefinition, missing_variant: list[Variant]
) -> None:
    detail = build_trait_detail(simple_trait, missing_variant)

    rsid = detail.rsids[0]

    assert rsid.status == "missing"
    assert "No genotype detected" in rsid.meaning
    assert "did not include" in rsid.status_explanation


# --- Test odds ratio and score inclusion in detail ---


def test_trait_detail_includes_odds_ratio(
    simple_trait: TraitDefinition, matching_variant: list[Variant]
) -> None:
    detail = build_trait_detail(simple_trait, matching_variant)

    rsid = detail.rsids[0]

    assert rsid.odds_ratio is None or isinstance(rsid.odds_ratio, float)
    assert isinstance(rsid.score, float)
    assert detail.headline
    assert detail.headline_tooltip
    assert detail.outcome_summary
    assert detail.result_badge_tooltip
    assert detail.practical_takeaway
    assert detail.simple_explanation
    assert detail.technical_explanation
    assert detail.research_spotlight
    assert detail.calculation_summary


# --- Test multiple rules and real-world case ---


def test_multiple_rules_aggregation() -> None:
    trait = TraitDefinition(
        id="multi",
        name="Multi",
        category="health",
        description="",
        simple_summary="",
        technical_summary="",
        rules=[
            CuratedTraitRule(
                rsid="rs1",
                genotype_meanings=[
                    GenotypeInterpretation(genotype=["AA"], meaning="good", score=0.5)
                ],
                weight=1.0,
                description="r1",
            ),
            CuratedTraitRule(
                rsid="rs2",
                genotype_meanings=[
                    GenotypeInterpretation(genotype=["AA"], meaning="bad", score=-0.5)
                ],
                weight=1.0,
                description="r2",
            ),
        ],
    )

    variants = [
        Variant(rsid="rs1", chromosome="1", position=1, genotype=["A", "A"]),
        Variant(rsid="rs2", chromosome="1", position=2, genotype=["A", "A"]),
    ]

    evaluation = evaluate_trait(trait, variants)

    assert evaluation.score == 0  # cancel out
    assert evaluation.result == "inconclusive"


# --- Test real-world case with partial data ---


def test_real_lactose_case() -> None:
    trait = next(t for t in list_trait_definitions() if t.id == "lactose_intolerance")
    variants = [
        Variant(rsid="rs4988235", chromosome="2", position=1, genotype=["C", "T"]),
        Variant(rsid="rs182549", chromosome="2", position=1, genotype=["T", "T"]),
    ]

    evaluation = evaluate_trait(trait, variants)

    assert evaluation.coverage > 0
    assert evaluation.result in ["likely", "unlikely", "inconclusive"]
