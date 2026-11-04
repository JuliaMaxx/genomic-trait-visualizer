from backend.models import TraitAnalysisDetail, TraitAnalysisSummary, Variant
from backend.services.trait_curation import (
    build_trait_result,
    evaluate_trait,
    list_trait_definitions,
)
from backend.services.trait_curation.catalog import (
    build_trait_detail,
    get_trait_definition,
)


def calculate_traits(variants: list[Variant]) -> list[TraitAnalysisSummary]:
    """
    Calculate traits based on provided variants.

    Builds a fast lookup map for variants, normalizes genotypes for comparison,
    treats rules as OR conditions (independent signals), tracks missing SNPs,
    and calculates confidence based on data availability.

    Returns all trait analysis summaries sorted by trait ID.
    """
    normalized_variants = [
        variant if isinstance(variant, Variant) else Variant(**variant)
        for variant in variants
    ]
    results: list[TraitAnalysisSummary] = []

    for trait in list_trait_definitions():
        evaluation = evaluate_trait(trait, normalized_variants)
        result = build_trait_result(evaluation)
        results.append(result)

    # Sort results by trait_id for deterministic output
    results.sort(key=lambda r: r.trait_id)

    return results


def calculate_single_trait(
    trait_id: str, variants: list[Variant]
) -> TraitAnalysisDetail | None:
    """Evaluate a single trait by its ID using the provided variants."""
    trait = get_trait_definition(trait_id)
    if trait is None:
        return None

    normalized_variants = [
        variant if isinstance(variant, Variant) else Variant(**variant)
        for variant in variants
    ]
    return build_trait_detail(trait, normalized_variants)
