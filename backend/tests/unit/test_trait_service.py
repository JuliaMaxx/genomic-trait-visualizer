from backend.models import Variant
from backend.services.trait_service import calculate_single_trait, calculate_traits

EXPECTED_IDS = {
    "lactose_intolerance",
    "caffeine_metabolism",
    "alcohol_flush",
    "eye_color",
    "bitter_taste",
}


def variant(rsid: str, genotype: str | None) -> Variant:
    alleles = list(genotype) if genotype is not None else None
    return Variant(
        rsid=rsid,
        chromosome="1",
        position=1000,
        genotype=alleles,
    )


def test_summary_includes_all_catalog_traits() -> None:
    results = calculate_traits([])

    assert {result.trait_id for result in results} == EXPECTED_IDS
    assert [result.trait_id for result in results] == sorted(EXPECTED_IDS)


def test_no_user_genotypes_are_explicitly_missing() -> None:
    results = calculate_traits([])
    lactose = next(
        result for result in results if result.trait_id == "lactose_intolerance"
    )

    assert lactose.result == "inconclusive"
    assert lactose.coverage == 0
    assert lactose.confidence == 0
    assert [rule.rsid for rule in lactose.rule_statuses] == [
        "rs4988235",
        "rs182549",
    ]
    assert all(rule.status == "missing" for rule in lactose.rule_statuses)


def test_observed_and_matched_genotypes_are_reported() -> None:
    results = calculate_traits([variant("rs4988235", "CC")])
    lactose = next(
        result for result in results if result.trait_id == "lactose_intolerance"
    )

    assert [rule.status for rule in lactose.rule_statuses] == [
        "matched",
        "missing",
    ]
    assert 0 < lactose.coverage < 1


def test_genotypes_are_order_independent() -> None:
    forward = calculate_traits([variant("rs762551", "AG")])
    reverse = calculate_traits([variant("rs762551", "GA")])

    assert forward == reverse


def test_observed_but_unmatched_genotype_is_not_missing() -> None:
    detail = calculate_single_trait("caffeine_metabolism", [variant("rs762551", "TT")])

    assert detail is not None
    assert detail.analysis.rules[0].rsid == "rs762551"
    assert detail.analysis.rules[0].status == "unmatched"
    assert detail.analysis.rules[0].status == "unmatched"
    assert detail.analysis.rules[0].interpretation is None
    assert "no curated interpretation" in detail.analysis.rules[0].status_explanation


def test_missing_genotype_has_unavailable_score_and_specific_copy() -> None:
    detail = calculate_single_trait("caffeine_metabolism", [])

    assert detail is not None
    assert detail.analysis.score is None
    assert detail.analysis.rules[0].status == "missing"
    assert "not enough dna data" in detail.analysis.result_content.headline.lower()
    assert any(
        "score is unavailable" in section.body.lower()
        for section in detail.analysis.calculation_explanation
    )


def test_single_trait_unknown_id_returns_none() -> None:
    assert calculate_single_trait("not_a_trait", []) is None


def test_duplicate_rsids_use_last_observed_variant() -> None:
    details = calculate_single_trait(
        "lactose_intolerance",
        [variant("rs4988235", "TT"), variant("rs4988235", "CC")],
    )

    assert details is not None
    assert details.analysis.rules[0].user_genotype == ["C", "C"]
    assert details.analysis.rules[0].status == "matched"


def test_detail_contains_catalog_and_analysis_responsibilities_separately() -> None:
    detail = calculate_single_trait("lactose_intolerance", [variant("rs4988235", "CC")])

    assert detail is not None
    assert detail.trait.id == "lactose_intolerance"
    assert detail.trait.rules[0].rsid == "rs4988235"
    assert detail.analysis.rules[0].rsid == "rs4988235"
    assert detail.analysis.rules[0].status == "matched"
    assert detail.analysis.calculation_explanation
