import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast

from backend.models import (
    CuratedTraitRule,
    EvaluatedRule,
    GenotypeInterpretation,
    RawCatalog,
    RawCatalogDict,
    RawTrait,
    TraitCatalog,
    TraitDefinition,
    TraitDetail,
    TraitEvaluation,
    TraitResult,
    TraitRsidDetail,
    Variant,
)

CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "traits.json"


def _load_raw_catalog() -> RawCatalog:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return cast(RawCatalogDict, data)

    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return cast(list[RawTrait], data)

    raise ValueError("Invalid catalog format: expected dict or list of dicts")


def _parse_catalog_dict(data: RawCatalogDict) -> tuple[str, list[RawTrait]]:
    return data.get("version", "1.0"), data.get("traits", [])


def _parse_catalog_list(data: list[RawTrait]) -> tuple[str, list[RawTrait]]:
    return "1.0", data


def _coerce_catalog(raw_catalog: RawCatalog) -> TraitCatalog:
    if isinstance(raw_catalog, dict):
        version, raw_traits = _parse_catalog_dict(raw_catalog)
    else:
        version, raw_traits = _parse_catalog_list(raw_catalog)
    traits = [TraitDefinition.model_validate(trait) for trait in raw_traits]
    return TraitCatalog(version=version, traits=traits)


@lru_cache(maxsize=1)
def load_trait_catalog() -> TraitCatalog:
    return _coerce_catalog(_load_raw_catalog())


@lru_cache(maxsize=1)
def _trait_lookup_by_id() -> dict[str, TraitDefinition]:
    return {trait.id: trait for trait in load_trait_catalog().traits}


def list_trait_definitions() -> list[TraitDefinition]:
    return list(load_trait_catalog().traits)


def get_trait_definition(trait_id: str) -> TraitDefinition | None:
    return _trait_lookup_by_id().get(trait_id)


def _normalize_genotype(genotype: str | list[str]) -> str:
    if isinstance(genotype, list):
        cleaned = "".join(genotype).replace(" ", "").replace("/", "").upper()
    else:
        cleaned = genotype.replace(" ", "").replace("/", "").upper()
    if len(cleaned) == 2:
        return "".join(sorted(cleaned))
    return cleaned


def _normalize_genotype_alleles(genotype: str | list[str]) -> list[str]:
    if isinstance(genotype, list):
        return [allele.strip().upper() for allele in genotype if allele.strip()]

    normalized = _normalize_genotype(genotype)
    return list(normalized)


def _normalize_genotypes(genotype: str | list[str]) -> set[str]:
    if isinstance(genotype, str):
        return {_normalize_genotype(genotype)}
    return {_normalize_genotype(g) for g in genotype}


def _find_interpretation(
    rule: CuratedTraitRule,
    user_genotype: str,
) -> GenotypeInterpretation | None:
    for interpretation in sorted(
        rule.genotype_meanings,
        key=lambda entry: abs(entry.score),
        reverse=True,
    ):
        if user_genotype in _normalize_genotypes(interpretation.genotype):
            return interpretation
    return None


def _interpretation_weight(
    rule: CuratedTraitRule, interpretation: GenotypeInterpretation
) -> float:
    direction = (
        1.0 if interpretation.score > 0 else -1.0 if interpretation.score < 0 else 0.0
    )
    if direction == 0.0:
        return 0.0

    score_hint = abs(interpretation.score) if interpretation.score != 0 else 0.5
    if rule.odds_ratio and rule.odds_ratio > 0:
        return direction * score_hint * math.log(rule.odds_ratio)

    return direction * score_hint


def _result_from_score(score: float) -> Literal["likely", "unlikely", "inconclusive"]:
    if score >= 0.25:
        return "likely"
    if score <= -0.25:
        return "unlikely"
    return "inconclusive"


def _evidence_modifier(
    trait: TraitDefinition, evaluated_rules: list[EvaluatedRule]
) -> float:
    matched_weights = [
        abs(_interpretation_weight(evaluated.rule, evaluated.interpretation))
        for evaluated in evaluated_rules
        if evaluated.interpretation is not None
    ]

    if not matched_weights:
        return 0.0

    mean_evidence = sum(matched_weights) / len(matched_weights)
    level_bonus = {
        "strong": 1.0,
        "moderate": 0.8,
        "limited": 0.6,
    }.get(trait.evidence_level, 0.8)

    return min(1.0, mean_evidence * level_bonus)


def _rule_genotypes(rule: CuratedTraitRule) -> list[str] | None:
    genotypes: list[str] = []

    for interpretation in rule.genotype_meanings:
        for genotype in interpretation.genotype:
            normalized = _normalize_genotype(genotype)
            if normalized not in genotypes:
                genotypes.append(normalized)

    return genotypes or None


def evaluate_trait(trait: TraitDefinition, variants: list[Variant]) -> TraitEvaluation:
    # --- 1. Fast lookup for user variants ---
    variant_lookup = {variant.rsid: variant for variant in variants}

    # --- 2. Containers for results ---
    matched_rules: list[CuratedTraitRule] = []
    missing_rsids: set[str] = set()
    evaluated_rules: list[EvaluatedRule] = []

    # --- 3. Weight tracking ---
    total_weight = sum(max(rule.weight, 0.0) for rule in trait.rules)
    observed_weight = 0.0  # rules where we HAVE genotype data
    matched_weight = 0.0  # rules where interpretation matched
    weighted_score_sum = 0.0  # accumulated score

    # --- 4. Iterate rules in priority order ---
    for rule in sorted(
        trait.rules,
        key=lambda r: r.priority if r.priority is not None else 1000,
    ):
        variant = variant_lookup.get(rule.rsid)

        # --- 4A. Missing genotype ---
        if variant is None or not variant.genotype:
            missing_rsids.add(rule.rsid)
            evaluated_rules.append(
                EvaluatedRule(rule=rule, user_genotype=None, interpretation=None)
            )
            continue

        # --- 4B. Normalize genotype ---
        normalized_user_genotype = _normalize_genotype_alleles(variant.genotype)
        user_genotype = _normalize_genotype(normalized_user_genotype)

        # We observed this rule (data exists)
        observed_weight += max(rule.weight, 0.0)

        # --- 4C. Find interpretation ---
        interpretation = _find_interpretation(rule, user_genotype)

        if interpretation:
            matched_rules.append(rule)
            matched_weight += max(rule.weight, 0.0)

            # Add weighted contribution
            weighted_score_sum += max(rule.weight, 0.0) * _interpretation_weight(
                rule, interpretation
            )

        # --- 4D. Store evaluation snapshot ---
        evaluated_rules.append(
            EvaluatedRule(
                rule=rule,
                user_genotype=normalized_user_genotype,
                interpretation=interpretation,
            )
        )

    # --- 5. Coverage (how much data we had) ---
    coverage = observed_weight / total_weight if total_weight > 0 else 0.0

    # --- 6. Score (normalized against ALL possible signal) ---
    score = weighted_score_sum / total_weight if total_weight > 0 else 0.0

    # --- 7. Human-readable result ---
    result = _result_from_score(score)

    # --- 8. Confidence (how reliable this evaluation is) ---
    confidence = coverage * _evidence_modifier(trait, evaluated_rules)

    # --- 9. Notes for UI / transparency ---
    notes = [
        f"Category: {trait.category}",
        f"Evidence level: {trait.evidence_level}",
        f"Coverage: {coverage:.2f}",
        f"Score: {score:.2f}",
        f"Result: {result}",
        "Confidence reflects data completeness and evidence strength, not certainty.",
        "Educational summary only; not diagnostic.",
    ]

    # --- 10. Final object ---
    return TraitEvaluation(
        trait=trait,
        matched_rules=matched_rules,
        missing_rsids=sorted(missing_rsids),
        coverage=coverage,
        confidence=confidence,
        score=score,
        result=result,
        notes=notes,
        evaluated_rules=evaluated_rules,
    )


def build_trait_result(
    evaluation: TraitEvaluation,
) -> TraitResult:
    return TraitResult(
        trait_id=evaluation.trait.id,
        name=evaluation.trait.name,
        category=evaluation.trait.category,
        missing_rsids=evaluation.missing_rsids,
        matched_rsids=[
            e.rule.rsid for e in evaluation.evaluated_rules if e.interpretation
        ],
        confidence=evaluation.confidence,
        result=evaluation.result,
        simple_summary=evaluation.trait.simple_summary,
    )


def build_trait_detail(trait: TraitDefinition, variants: list[Variant]) -> TraitDetail:
    evaluation = evaluate_trait(trait, variants)
    rsids: list[TraitRsidDetail] = []

    for evaluated in evaluation.evaluated_rules:
        status: Literal["matched", "no_match", "missing"]
        if evaluated.user_genotype is None:
            meaning = "No genotype detected in uploaded data for this rsID."
            status = "missing"
        elif evaluated.interpretation is None:
            meaning = evaluated.rule.default_meaning or "No interpretation available."
            status = "no_match"
        else:
            meaning = evaluated.interpretation.meaning
            status = "matched"

        effect = (
            evaluated.interpretation.effect
            if evaluated.interpretation and evaluated.interpretation.effect
            else evaluated.rule.effect or evaluated.rule.description
        )

        rsids.append(
            TraitRsidDetail(
                rsid=evaluated.rule.rsid,
                genotype=_rule_genotypes(evaluated.rule),
                user_genotype=evaluated.user_genotype,
                gene=evaluated.rule.gene,
                effect=effect,
                odds_ratio=evaluated.rule.odds_ratio,
                score=(
                    evaluated.interpretation.score if evaluated.interpretation else None
                ),
                meaning=meaning,
                rule_description=evaluated.rule.description,
                status=status,
            )
        )

    return TraitDetail(
        id=evaluation.trait.id,
        name=evaluation.trait.name,
        category=evaluation.trait.category,
        result=evaluation.result,
        confidence=evaluation.confidence,
        description=evaluation.trait.description,
        simple_summary=evaluation.trait.simple_summary,
        technical_summary=evaluation.trait.technical_summary,
        evidence_level=evaluation.trait.evidence_level,
        keywords=evaluation.trait.keywords,
        coverage=evaluation.coverage,
        score=evaluation.score,
        rsids=rsids,
        sources=evaluation.trait.sources,
        notes=evaluation.notes,
    )
