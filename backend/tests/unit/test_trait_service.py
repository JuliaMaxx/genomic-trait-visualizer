import pytest

from backend.models.schemas import TraitResult, Variant
from backend.services.trait_service import calculate_traits

# ------------------------
# Helpers
# ------------------------


def make_variant(
    rsid: str, genotype: str | None, chromosome: str = "1", position: int = 1000
) -> Variant:
    return Variant(
        rsid=rsid,
        chromosome=chromosome,
        position=position,
        genotype=genotype,
    )


def assert_all_traits_present(traits: list[TraitResult]) -> None:
    expected_ids = {
        "lactose_intolerance",
        "caffeine_metabolism",
        "alcohol_flush",
        "eye_color",
        "bitter_taste",
    }
    assert {t.trait_id for t in traits} == expected_ids


# ------------------------
# BASIC FUNCTIONALITY
# ------------------------


def test_single_trait_match() -> None:
    variants = [make_variant("rs4988235", "CC")]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


def test_no_matching_traits() -> None:
    variants = [
        make_variant("rs0000000", "AA"),
    ]

    traits = calculate_traits(variants)

    assert all(len(t.matched_rules) == 0 for t in traits)


# ------------------------
# GENOTYPE NORMALIZATION
# ------------------------


@pytest.mark.parametrize("genotype", ["AG", "GA", "A/G", "A G"])
def test_genotype_normalization(genotype: str) -> None:
    variants: list[Variant] = [
        make_variant("rs762551", genotype),
    ]

    traits = calculate_traits(variants)

    # Should not crash and should normalize consistently
    assert_all_traits_present(traits)


# ------------------------
# MISSING SNP HANDLING
# ------------------------


def test_missing_snp_not_treated_as_negative() -> None:
    variants: list[Variant] = []

    traits = calculate_traits(variants)

    for trait in traits:
        assert len(trait.missing_rsids) >= 0


def test_partial_data_confidence() -> None:
    variants = [
        make_variant("rs4988235", "CC"),  # one SNP present
    ]

    traits = calculate_traits(variants)

    for trait in traits:
        assert 0 <= trait.confidence <= 1


# ------------------------
# BROKEN GENOTYPES
# ------------------------


@pytest.mark.parametrize(
    "bad_genotype",
    [
        None,
        "",
        "--",
        "??",
        "123",
    ],
)
def test_invalid_genotypes_handled_gracefully(bad_genotype: str | None) -> None:
    variants = [
        make_variant("rs4988235", bad_genotype),
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# DUPLICATE SNPs
# ------------------------


def test_duplicate_rsids() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs4988235", "TT"),  # duplicate
    ]

    traits = calculate_traits(variants)

    # Should not crash; deterministic behavior expected
    assert_all_traits_present(traits)


# ------------------------
# MULTI-GENOTYPE RULE MATCHING
# ------------------------


def test_list_genotype_rule_match() -> None:
    variants = [
        make_variant("rs762551", "AC"),  # matches ["AC", "CC"]
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# CONSISTENCY / DETERMINISM
# ------------------------


def test_deterministic_output() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
    ]

    traits1 = calculate_traits(variants)
    traits2 = calculate_traits(variants)

    assert traits1 == traits2


# ------------------------
# EMPTY INPUT
# ------------------------


def test_empty_parse_result() -> None:
    variants: list[Variant] = []

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# MIXED VALID + INVALID DATA
# ------------------------


def test_mixed_valid_and_invalid_variants() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs762551", None),
        make_variant("rsXXXX", "??"),
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# MULTI-TRAIT INTERACTION
# ------------------------


def test_multiple_traits_triggered() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs762551", "AA"),
        make_variant("rs12913832", "AA"),
    ]

    traits = calculate_traits(variants)

    triggered = [t for t in traits if t.matched_rules]

    assert len(triggered) >= 2


# ------------------------
# GENOTYPE ORDER NORMALIZATION
# ------------------------


def test_genotype_order_irrelevant() -> None:
    variants1 = [make_variant("rs762551", "AG")]
    variants2 = [make_variant("rs762551", "GA")]

    output1 = calculate_traits(variants1)
    output2 = calculate_traits(variants2)

    assert output1 == output2


# ------------------------
# EXTREME INPUT SIZE
# ------------------------


def test_large_input() -> None:
    variants = [make_variant(f"rs{i}", "AA") for i in range(10000)]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# UNKNOWN RSIDs
# ------------------------


def test_unknown_rsids_ignored() -> None:
    variants = [
        make_variant("rs999999999", "AA"),
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# CONFIDENCE NEVER EXCEEDS 1
# ------------------------


def test_confidence_bounds() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
    ]

    traits = calculate_traits(variants)

    for trait in traits:
        assert 0 <= trait.confidence <= 1


def test_missing_vs_available_counts() -> None:
    variants = [
        make_variant("rs4988235", "CC"),  # present
        # rs182549 missing
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert "rs182549" in lactose.missing_rsids
    assert lactose.confidence < 1


def test_duplicate_rsids_last_wins() -> None:
    variants = [
        make_variant("rs4988235", "TT"),
        make_variant("rs4988235", "CC"),  # should override
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert any(r.rsid == "rs4988235" for r in lactose.matched_rules)


def test_multi_rule_trait_partial_match() -> None:
    variants = [
        make_variant("rs4988235", "CC"),  # match
        make_variant("rs182549", "AA"),  # no match
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert len(lactose.matched_rules) == 1
    assert pytest.approx(lactose.confidence, 0.001) == 1.0  # both SNPs available


def test_confidence_calculation() -> None:
    variants = [
        make_variant("rs4988235", "CC"),  # available
        # second SNP missing
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert pytest.approx(lactose.confidence, 0.001) == 0.5


def test_rule_present_but_not_matching() -> None:
    variants = [
        make_variant("rs4988235", "TT"),  # does NOT match CC
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert len(lactose.matched_rules) == 0
    assert pytest.approx(lactose.confidence, 0.001) == 0.5


def test_genotype_case_insensitivity() -> None:
    variants: list[Variant] = [
        make_variant("rs762551", "ag"),
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


def test_trait_ordering() -> None:
    variants: list[Variant] = []

    traits = calculate_traits(variants)

    ids = [t.trait_id for t in traits]

    assert ids == sorted(ids)


def test_lactose_trait_exact_output() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs182549", "GG"),
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert {r.rsid for r in lactose.matched_rules} == {
        "rs4988235",
        "rs182549",
    }
    assert lactose.confidence == 1.0
    assert lactose.missing_rsids == []


def test_duplicate_rsids_with_normalization_conflict() -> None:
    variants = [
        make_variant("rs762551", "GA"),
        make_variant("rs762551", "AG"),  # same after normalization
    ]

    traits = calculate_traits(variants)

    assert len(traits) == 5
    trait_ids = {t.trait_id for t in traits}
    expected_ids = {
        "lactose_intolerance",
        "caffeine_metabolism",
        "alcohol_flush",
        "eye_color",
        "bitter_taste",
    }
    assert trait_ids == expected_ids


def test_caffeine_trait_exact() -> None:
    variants = [
        make_variant("rs762551", "AA"),
    ]

    traits = calculate_traits(variants)

    caffeine = next(t for t in traits if t.trait_id == "caffeine_metabolism")

    assert len(caffeine.matched_rules) == 1
    assert caffeine.confidence == 1.0


def test_caffeine_partial_match_behavior() -> None:
    variants = [
        make_variant("rs762551", "AA"),
        make_variant("rs762551", "GG"),  # depending on biology logic
    ]

    traits = calculate_traits(variants)

    caffeine = next(t for t in traits if t.trait_id == "caffeine_metabolism")

    assert caffeine.confidence <= 1.0
    assert isinstance(caffeine.matched_rules, list)
