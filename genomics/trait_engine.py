import pandas as pd

from backend.models.schemas import Variant


def calculate_traits(user_variants: list[Variant]) -> dict[str, float]:

    trait_data = pd.read_csv("data/trait_variants.csv")

    results = {}

    for trait in trait_data["trait"].unique():

        snps = trait_data[trait_data["trait"] == trait]

        score = 0
        total = 0

        for _, row in snps.iterrows():

            rsid = row["rsid"]
            effect = row["effect_allele"]
            weight = row["weight"]

            variant = next((v for v in user_variants if v.rsid == rsid), None)

            if variant and variant.genotype is not None and effect in variant.genotype:
                score += weight

            total += weight

        probability = score / total if total > 0 else 0

        results[trait] = probability

    return results
