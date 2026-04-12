import json
from pathlib import Path

from backend.models.schemas import TraitResult, TraitRule, Variant


def normalize_genotype(genotype: str) -> str:
    """Normalize genotype string by removing separators and sorting alleles."""
    if not genotype:
        return ""
    # Remove spaces and slashes
    cleaned = genotype.replace(" ", "").replace("/", "").upper()
    # Assume two alleles and sort them
    if len(cleaned) == 2:
        return "".join(sorted(cleaned))
    else:
        # For other cases, return as is (though typically should be 2)
        return cleaned


def calculate_traits(variants: list[Variant]) -> list[TraitResult]:
    """
    Calculate traits based on provided variants.

    Builds a fast lookup map for variants, normalizes genotypes for comparison,
    treats rules as OR conditions (independent signals), tracks missing SNPs,
    and calculates confidence based on data availability.

    Returns a list of TraitResult objects, sorted by trait_id for deterministic output.
    """
    # Load traits data
    traits_path = Path(__file__).parent.parent.parent / "data" / "traits.json"
    with open(traits_path, "r", encoding="utf-8") as f:
        traits_data = json.load(f)

    # Build fast lookup map: rsid -> Variant
    variant_lookup = {v.rsid: v for v in variants}

    results = []

    for trait in traits_data:
        trait_id = trait["id"]
        name = trait["name"]
        rules_data = trait["rules"]

        # Convert rules to TraitRule objects
        rules = [TraitRule(**r) for r in rules_data]

        matched_rules = []
        missing_rsids_set = set()
        total_rules = len(rules)
        available_count = 0  # SNPs with data available

        for rule in rules:
            if rule.rsid in variant_lookup:
                variant = variant_lookup[rule.rsid]
                if variant.genotype:
                    # Normalize variant genotype
                    norm_var = normalize_genotype(variant.genotype)
                    # Normalize rule genotypes
                    if isinstance(rule.genotype, str):
                        norm_rule_genos = [normalize_genotype(rule.genotype)]
                    elif isinstance(rule.genotype, list):
                        norm_rule_genos = [normalize_genotype(g) for g in rule.genotype]
                    else:
                        norm_rule_genos = []
                    # Check if any rule genotype matches
                    if norm_var in norm_rule_genos:
                        matched_rules.append(rule)
                    available_count += 1
                else:
                    # Genotype is None, treat as missing
                    missing_rsids_set.add(rule.rsid)
            else:
                # RSID not in variants, missing
                missing_rsids_set.add(rule.rsid)

        # Calculate confidence based on data availability
        confidence = available_count / total_rules if total_rules > 0 else 0.0

        # Sort for deterministic output
        matched_rules.sort(key=lambda r: r.rsid)
        missing_rsids = sorted(missing_rsids_set)

        # Notes: optional scientific notes (empty for now, extensible)
        notes: list[str] = []

        result = TraitResult(
            trait_id=trait_id,
            name=name,
            matched_rules=matched_rules,
            missing_rsids=missing_rsids,
            confidence=confidence,
            notes=notes,
        )
        results.append(result)

    # Sort results by trait_id for deterministic output
    results.sort(key=lambda r: r.trait_id)

    return results
