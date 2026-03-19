from backend.models.schemas import TraitResult, Variant
from genomics.trait_engine import calculate_traits


def analyze_traits(variants: list[Variant]) -> list[TraitResult]:

    trait_results = calculate_traits(variants)

    results: list[TraitResult] = []

    for trait, probability in trait_results.items():

        results.append(TraitResult(trait=trait, probability=probability))

    return results
