import pytest

from backend.models.schemas import TraitResult, Variant
from backend.services.trait_service import calculate_single_trait, calculate_traits

# ------------------------
# Helpers
# ------------------------


def to_alleles(genotype: str | None) -> list[str] | None:
    if genotype is None:
        return None
    return [allele for allele in genotype if allele not in {"/", " "}]


def make_variant(
    rsid: str,
    genotype: str | None,
    chromosome: str = "1",
    position: int = 1000,
) -> Variant:
    return Variant(
        rsid=rsid,
        chromosome=chromosome,
        position=position,
        genotype=to_alleles(genotype),
    )


EXPECTED_IDS = {
    "lactose_intolerance",
    "caffeine_metabolism",
    "alcohol_flush",
    "eye_color",
    "bitter_taste",
}


def assert_all_traits_present(traits: list[TraitResult]) -> None:
    assert {t.trait_id for t in traits} == EXPECTED_IDS


# ------------------------
# BASIC FUNCTIONALITY
# ------------------------


def test_returns_all_traits() -> None:
    traits = calculate_traits([])
    assert_all_traits_present(traits)


def test_single_trait_match() -> None:
    variants = [make_variant("rs4988235", "CC")]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert "rs4988235" in lactose.matched_rsids


def test_no_matching_traits() -> None:
    variants = [make_variant("rs0000000", "AA")]

    traits = calculate_traits(variants)

    assert all(len(t.matched_rsids) == 0 for t in traits)


# ------------------------
# GENOTYPE NORMALIZATION
# ------------------------


@pytest.mark.parametrize("genotype", ["AG", "GA", "A/G", "A G"])
def test_genotype_normalization(genotype: str) -> None:
    variants = [make_variant("rs762551", genotype)]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# MISSING SNP HANDLING
# ------------------------


def test_missing_snp_recorded() -> None:
    traits = calculate_traits([])

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert "rs4988235" in lactose.missing_rsids
    assert "rs182549" in lactose.missing_rsids


def test_partial_data_confidence() -> None:
    variants = [make_variant("rs4988235", "CC")]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert 0 < lactose.confidence < 1


# ------------------------
# INVALID GENOTYPES
# ------------------------


@pytest.mark.parametrize("bad_genotype", [None, "", "--", "??", "123"])
def test_invalid_genotypes_handled_gracefully(
    bad_genotype: str | None,
) -> None:
    variants = [make_variant("rs4988235", bad_genotype)]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# DUPLICATES
# ------------------------


def test_duplicate_rsids_last_wins() -> None:
    variants = [
        make_variant("rs4988235", "TT"),
        make_variant("rs4988235", "CC"),
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert "rs4988235" in lactose.matched_rsids


# ------------------------
# MULTI RULE MATCHING
# ------------------------


def test_multi_rule_trait_match() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs182549", "GG"),
    ]

    traits = calculate_traits(variants)

    lactose = next(t for t in traits if t.trait_id == "lactose_intolerance")

    assert set(lactose.matched_rsids) == {"rs4988235", "rs182549"}
    assert 0 < lactose.confidence <= 1.0


# ------------------------
# DETERMINISM
# ------------------------


def test_deterministic_output() -> None:
    variants = [make_variant("rs4988235", "CC")]

    assert calculate_traits(variants) == calculate_traits(variants)


# ------------------------
# EMPTY INPUT
# ------------------------


def test_empty_input() -> None:
    traits = calculate_traits([])

    assert_all_traits_present(traits)


# ------------------------
# MIXED DATA
# ------------------------


def test_mixed_valid_invalid() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs762551", None),
        make_variant("rsXXXX", "??"),
    ]

    traits = calculate_traits(variants)

    assert_all_traits_present(traits)


# ------------------------
# MULTI TRAIT TRIGGER
# ------------------------


def test_multiple_traits_triggered() -> None:
    variants = [
        make_variant("rs4988235", "CC"),
        make_variant("rs762551", "AA"),
        make_variant("rs12913832", "AA"),
    ]

    traits = calculate_traits(variants)

    triggered = [t for t in traits if t.matched_rsids]

    assert len(triggered) >= 2


# ------------------------
# ORDERING
# ------------------------


def test_trait_ordering() -> None:
    traits = calculate_traits([])

    ids = [t.trait_id for t in traits]

    assert ids == sorted(ids)


# ------------------------
# CONFIDENCE BOUNDS
# ------------------------


def test_confidence_bounds() -> None:
    variants = [make_variant("rs4988235", "CC")]

    traits = calculate_traits(variants)

    for trait in traits:
        assert 0 <= trait.confidence <= 1


# ------------------------
# RESULT FIELD
# ------------------------


def test_result_values_valid() -> None:
    variants = [make_variant("rs4988235", "CC")]

    traits = calculate_traits(variants)

    valid = {"likely", "unlikely", "inconclusive"}

    for trait in traits:
        assert trait.result in valid


# ------------------------
# SINGLE TRAIT CALCULATION
# ------------------------


def test_calculate_single_trait_valid_trait() -> None:
    variants = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    result = calculate_single_trait("lactose_intolerance", variants)

    assert result is not None
    assert result.id == "lactose_intolerance"
    assert result.result in {"likely", "unlikely", "inconclusive"}
    assert isinstance(result.rsids, list)


def test_calculate_single_trait_invalid_id() -> None:
    result = calculate_single_trait("not_a_trait", [])

    assert result is None


def test_calculate_single_trait_changes_with_genotype() -> None:
    variants_cc = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    variants_tt = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["T", "T"])
    ]

    result_cc = calculate_single_trait("lactose_intolerance", variants_cc)
    result_tt = calculate_single_trait("lactose_intolerance", variants_tt)

    assert result_cc is not None
    assert result_tt is not None
    assert result_cc.score != result_tt.score


def test_trait_detail_structure_complete() -> None:
    variants = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    detail = calculate_single_trait("lactose_intolerance", variants)

    assert detail is not None

    # core fields
    assert detail.id
    assert detail.name
    assert detail.category

    # explanation layer
    assert detail.simple_summary
    assert detail.technical_summary

    # computed layer
    assert isinstance(detail.rsids, list)
    assert hasattr(detail, "confidence")
    assert hasattr(detail, "score")

    # metadata
    assert detail.sources is not None
    assert detail.keywords is not None


def test_rsid_statuses_present() -> None:
    variants = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    detail = calculate_single_trait("lactose_intolerance", variants)

    assert detail is not None
    statuses = {r.status for r in detail.rsids}

    assert statuses.issubset({"matched", "no_match", "missing"})
    assert len(detail.rsids) > 0


def test_confidence_bounds_single_trait() -> None:
    variants = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    detail = calculate_single_trait("lactose_intolerance", variants)

    assert detail is not None
    assert 0 <= detail.confidence <= 1


# ------------------------
# DETERMINISM
# ------------------------


def test_single_trait_deterministic() -> None:
    variants = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    a = calculate_single_trait("lactose_intolerance", variants)
    b = calculate_single_trait("lactose_intolerance", variants)

    assert a is not None
    assert b is not None
    assert a == b


@pytest.mark.parametrize(
    "variants",
    [
        [],
        [
            {
                "rsid": "rs4988235",
                "chromosome": "1",
                "position": 1000,
                "genotype": ["C", "C"],
            }
        ],
        [
            {
                "rsid": "rs762551",
                "chromosome": "1",
                "position": 1000,
                "genotype": ["A", "G"],
            }
        ],
        [
            {
                "rsid": "rs671",
                "chromosome": "1",
                "position": 1000,
                "genotype": ["?", "?"],
            }
        ],
        [
            {
                "rsid": "rs000000",
                "chromosome": "1",
                "position": 1000,
                "genotype": ["A", "A"],
            }
        ],
    ],
)
def test_single_trait_never_crashes(
    variants: list[Variant],
) -> None:
    result = calculate_single_trait("lactose_intolerance", variants)

    assert result is None or result.confidence >= 0


def test_trait_result_structure() -> None:
    variants: list[Variant] = [
        Variant(rsid="rs4988235", chromosome="1", position=1000, genotype=["C", "C"])
    ]

    result = calculate_single_trait("lactose_intolerance", variants)

    assert result is not None
    assert hasattr(result, "rsids")

    for r in result.rsids:
        assert r.status in {"missing", "no_match", "matched"}
