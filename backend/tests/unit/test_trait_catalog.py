import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.models import (
    CuratedTraitRule,
    TraitCatalog,
    Variant,
)
from backend.services.trait_curation.catalog import (
    _find_interpretation,
    _normalize_genotype,
    build_trait_detail,
    evaluate_trait,
    get_rsid_detail,
    list_rsid_catalog,
    list_trait_definitions,
    load_trait_catalog,
    search_catalog,
)


def test_published_catalog_fully_validates() -> None:
    data = json.loads(Path("data/traits.json").read_text(encoding="utf-8"))
    catalog = TraitCatalog.model_validate(data)

    assert len(catalog.traits) == 5
    assert sum(len(trait.rules) for trait in catalog.traits) == 6
    assert all(trait.sources for trait in catalog.traits)
    assert all(
        len(trait.result_content.model_fields_set) == 3 for trait in catalog.traits
    )


def test_catalog_loader_is_the_validated_source() -> None:
    assert load_trait_catalog() == TraitCatalog.model_validate(
        json.loads(Path("data/traits.json").read_text(encoding="utf-8"))
    )


def test_published_rule_requires_explicit_odds_ratio_state() -> None:
    rule = list_trait_definitions()[0].rules[0].model_dump()
    del rule["odds_ratio"]

    with pytest.raises(ValidationError):
        CuratedTraitRule.model_validate(rule)


def test_odds_ratio_value_must_match_reported_state() -> None:
    rule = list_trait_definitions()[1].rules[0].model_dump()
    rule["odds_ratio"] = 1.5

    with pytest.raises(ValidationError):
        CuratedTraitRule.model_validate(rule)


def test_non_applicable_odds_ratio_is_distinct_from_not_reported() -> None:
    rules = [rule for trait in list_trait_definitions() for rule in trait.rules]
    reported = [rule for rule in rules if rule.odds_ratio_status == "reported"]
    not_reported = [rule for rule in rules if rule.odds_ratio_status == "not_reported"]

    assert all(rule.odds_ratio is not None for rule in reported)
    assert all(rule.odds_ratio is None for rule in not_reported)
    assert not any(rule.odds_ratio_status == "not_applicable" for rule in rules)


def test_catalog_rejects_unknown_fields() -> None:
    data = json.loads(Path("data/traits.json").read_text(encoding="utf-8"))
    data["traits"][0]["unexpected"] = "extra data must not be silently discarded"

    with pytest.raises(ValidationError):
        TraitCatalog.model_validate(data)


def test_genotype_interpretations_match_order_independently() -> None:
    rule = list_trait_definitions()[0].rules[0]

    assert _find_interpretation(rule, "CT") == _find_interpretation(
        rule, _normalize_genotype("TC")
    )
    assert _normalize_genotype("a/g") == "AG"


def test_analysis_distinguishes_missing_observed_and_matched() -> None:
    trait = next(
        trait for trait in list_trait_definitions() if trait.id == "lactose_intolerance"
    )
    evaluation = evaluate_trait(
        trait,
        [Variant(rsid="rs4988235", chromosome="2", position=1, genotype=["A", "A"])],
    )

    assert evaluation.evaluated_rules[0].status == "unmatched"
    assert evaluation.evaluated_rules[1].status == "missing"
    assert evaluation.observed_rsids == ["rs4988235"]
    assert evaluation.missing_rsids == ["rs182549"]
    assert evaluation.matched_rsids == []
    assert evaluation.score is None


def test_no_genotypes_do_not_report_a_zero_score() -> None:
    trait = list_trait_definitions()[0]

    evaluation = evaluate_trait(trait, [])
    detail = build_trait_detail(trait, [])

    assert evaluation.result == "inconclusive"
    assert evaluation.score is None
    assert detail.analysis.score is None
    assert "not enough dna data" in detail.analysis.result_content.headline.lower()


def test_rsid_list_and_detail_are_derived_from_curated_rules() -> None:
    catalog = list_rsid_catalog()
    detail = get_rsid_detail("rs4988235")

    assert any(item.rsid == "rs4988235" for item in catalog)
    assert detail is not None
    assert detail.rsid == "rs4988235"
    assert any(link.trait_id == "lactose_intolerance" for link in detail.traits)
    assert detail.genotype_meanings
    assert detail.sources


def test_search_response_is_one_consistent_result_list() -> None:
    result = search_catalog("lactose")

    assert result.query == "lactose"
    assert any(item.kind == "trait" for item in result.results)
    assert all(item.title and item.subtitle and item.url for item in result.results)


def test_search_filters_category() -> None:
    result = search_catalog("lactose", category="appearance")

    assert all(item.kind != "trait" for item in result.results)
    assert all("lactose_intolerance" not in item.url for item in result.results)
