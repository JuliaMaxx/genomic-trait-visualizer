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
    TraitContentSection,
    TraitDefinition,
    TraitDetail,
    TraitEvaluation,
    TraitResult,
    TraitResultContent,
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


def _format_genotype(genotype: list[str] | None) -> str:
    if not genotype:
        return "not available"
    return "".join(genotype)


def _coverage_summary(coverage: float) -> str:
    percent = round(coverage * 100)
    if coverage >= 0.99:
        return (
            "We found data for all markers used in this trait "
            f"({percent}% coverage)."
        )
    if coverage >= 0.66:
        return (
            "We found data for most markers used in this trait "
            f"({percent}% coverage)."
        )
    if coverage > 0:
        return (
            "We only found data for some of the markers used in this trait "
            f"({percent}% coverage)."
        )
    return "We could not find any of this trait's markers in the uploaded DNA file."


def _score_summary(score: float) -> str:
    rounded = f"{score:.2f}"
    if score >= 0.25:
        return (
            f"The combined marker score is {rounded}, which is above the "
            "'likely' threshold."
        )
    if score <= -0.25:
        return (
            f"The combined marker score is {rounded}, which is below the "
            "'unlikely' threshold."
        )
    return (
        f"The combined marker score is {rounded}, which stays in the middle "
        "'inconclusive' zone."
    )


def _result_summary(
    trait: TraitDefinition,
    result: Literal["likely", "unlikely", "inconclusive"],
) -> str:
    if result == "likely":
        return (
            f"This DNA pattern leans toward the '{trait.name}' outcome in "
            "this educational model."
        )
    if result == "unlikely":
        return (
            f"This DNA pattern leans away from the '{trait.name}' outcome in "
            "this educational model."
        )
    return (
        "This DNA pattern does not lean strongly enough in either direction "
        f"for '{trait.name}'."
    )


def _default_result_content(
    trait: TraitDefinition,
    result: Literal["likely", "unlikely", "inconclusive"],
) -> TraitResultContent:
    if result == "likely":
        return TraitResultContent(
            card_tooltip=(
                f"For {trait.name.lower()}, your observed markers lean toward the "
                "outcome highlighted on this card."
            ),
            headline=f"Your DNA leans toward {trait.name.lower()}.",
            headline_tooltip=(
                "This headline summarizes the direction of the educational model, "
                "not a guarantee about your real-world phenotype."
            ),
            outcome_summary=(
                "The combined marker pattern pointed clearly enough in the positive "
                "direction for this simplified model to label the trait as likely."
            ),
        )

    if result == "unlikely":
        return TraitResultContent(
            card_tooltip=(
                f"For {trait.name.lower()}, your observed markers lean away from the "
                "outcome highlighted on this card."
            ),
            headline=f"Your DNA leans away from {trait.name.lower()}.",
            headline_tooltip=(
                "This headline summarizes the direction of the educational model, "
                "not a guarantee about your real-world phenotype."
            ),
            outcome_summary=(
                "The combined marker pattern leaned clearly in the opposite "
                "direction, so this simplified model labeled the trait as unlikely."
            ),
        )

    return TraitResultContent(
        card_tooltip=(
            f"For {trait.name.lower()}, the markers found in your file did not "
            "create a strong enough signal to lean either way."
        ),
        headline=f"There is no strong genetic lean for {trait.name.lower()}.",
        headline_tooltip=(
            "This usually means the available markers were mixed, weak, or missing "
            "for this educational model."
        ),
        outcome_summary=(
            "The observed markers did not push the model far enough toward either "
            "side, so the result stayed inconclusive."
        ),
    )


def _get_result_content(
    trait: TraitDefinition,
    result: Literal["likely", "unlikely", "inconclusive"],
) -> TraitResultContent:
    return trait.result_content.get(result) or _default_result_content(trait, result)


def _contribution_from_interpretation(
    interpretation: GenotypeInterpretation | None,
) -> Literal["raises", "lowers", "neutral", "unknown"]:
    if interpretation is None:
        return "unknown"
    if interpretation.score > 0:
        return "raises"
    if interpretation.score < 0:
        return "lowers"
    return "neutral"


def _contribution_label(
    contribution: Literal["raises", "lowers", "neutral", "unknown"],
    result: Literal["likely", "unlikely", "inconclusive"],
) -> str:
    if contribution == "raises":
        return "Pushes the trait toward a likely result"
    if contribution == "lowers":
        return "Pushes the trait away from a likely result"
    if contribution == "neutral":
        return "Adds little directional signal"
    if result == "inconclusive":
        return "Could not be used in the final call"
    return "No usable signal from this marker"


def _explain_odds_ratio(odds_ratio: float | None) -> str | None:
    if odds_ratio is None:
        return None
    return (
        f"Odds ratio {odds_ratio:.2f} means this marker had a stronger-than-baseline "
        "association in the curated source material. It is not a direct probability."
    )


def _status_explanation(
    user_genotype: list[str] | None,
    interpretation: GenotypeInterpretation | None,
) -> str:
    if user_genotype is None:
        return (
            "This marker was part of the model, but your uploaded file did "
            "not include a usable genotype for it."
        )
    if interpretation is None:
        return (
            f"We observed genotype {_format_genotype(user_genotype)}, but it "
            "did not match a curated "
            "interpretation rule in this simplified educational dataset."
        )
    return (
        f"We observed genotype {_format_genotype(user_genotype)}, which "
        "matched one of the curated "
        "interpretation rules for this marker."
    )


def _fallback_simple_explanation(trait: TraitDefinition) -> list[TraitContentSection]:
    return [
        TraitContentSection(
            title="What this trait is about",
            body=trait.description or f"This trait explores {trait.name.lower()}.",
        ),
        TraitContentSection(
            title="How to read it",
            body=trait.simple_summary,
        ),
    ]


def _fallback_technical_explanation(
    trait: TraitDefinition,
) -> list[TraitContentSection]:
    return [
        TraitContentSection(
            title="Technical summary",
            body=trait.technical_summary,
        ),
        TraitContentSection(
            title="Model caveat",
            body=(
                "This is a simplified educational interpretation built from a "
                "curated subset of markers rather than a full clinical or "
                "population-scale polygenic model."
            ),
        ),
    ]


def _fallback_research_spotlight(
    trait: TraitDefinition,
) -> list[TraitContentSection]:
    return [
        TraitContentSection(
            title="Research context",
            body=(
                f"This educational trait is curated from literature linked to "
                f"{trait.name.lower()} and should be read as a learning-oriented "
                "summary of reported associations."
            ),
        )
    ]


def _fallback_practical_takeaway(
    result: Literal["likely", "unlikely", "inconclusive"],
) -> list[TraitContentSection]:
    if result == "inconclusive":
        first_body = (
            "Treat this as a prompt to observe real life rather than as a dead end. "
            "If the trait matters to you, compare the unclear genetic result with "
            "your own experience over time."
        )
    elif result == "likely":
        first_body = (
            "Use this as a gentle expectation, not a rule. If your lived experience "
            "matches the direction of the result, that consistency can help the trait "
            "feel more personally meaningful."
        )
    else:
        first_body = (
            "A result leaning away from the trait can still coexist with everyday "
            "experiences that look similar for other reasons. Keep behavior and "
            "context in the picture rather than treating the genotype as the whole story."  # noqa: E501
        )

    return [
        TraitContentSection(
            title="Use it as a starting hypothesis",
            body=first_body,
        ),
        TraitContentSection(
            title="Notice mismatch, not just matches",
            body=(
                "If your day-to-day experience disagrees with the genetic lean, that "
                "does not mean the model failed. It usually means environment, habits, "
                "ancestry background, or missing biology matters too."
            ),
        ),
    ]


def _fallback_mental_model(trait: TraitDefinition) -> list[TraitContentSection]:
    return [
        TraitContentSection(
            title="Curated marker",
            body=f"We begin with the SNPs chosen for {trait.name.lower()}.",
        ),
        TraitContentSection(
            title="Biological mechanism",
            body="Those markers point toward a gene, regulatory region, or receptor pathway.",  # noqa: E501
        ),
        TraitContentSection(
            title="Trait signal",
            body="The pathway direction is combined into a simplified trait-level lean.",  # noqa: E501
        ),
    ]


def _fallback_model_limit_summary(
    total_rules: int,
) -> str:
    return (
        f"This result is based on {total_rules} curated marker"
        f"{'s' if total_rules != 1 else ''} and a simplified educational model, "
        "so it may not capture full global genetic variation or every real-world factor."  # noqa: E501
    )


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
    matched_rsids = [
        e.rule.rsid for e in evaluation.evaluated_rules if e.interpretation
    ]
    observed_rsids = [
        e.rule.rsid for e in evaluation.evaluated_rules if e.user_genotype is not None
    ]

    result_content = _get_result_content(evaluation.trait, evaluation.result)

    return TraitResult(
        trait_id=evaluation.trait.id,
        name=evaluation.trait.name,
        category=evaluation.trait.category,
        description=evaluation.trait.description,
        missing_rsids=evaluation.missing_rsids,
        matched_rsids=matched_rsids,
        observed_rsids=observed_rsids,
        confidence=evaluation.confidence,
        coverage=evaluation.coverage,
        result=evaluation.result,
        simple_summary=evaluation.trait.simple_summary,
        user_summary=_result_summary(evaluation.trait, evaluation.result),
        explanation_preview=" ".join(
            [
                _coverage_summary(evaluation.coverage),
                _score_summary(evaluation.score),
            ]
        ),
        result_badge_tooltip=result_content.card_tooltip,
    )


def build_trait_detail(trait: TraitDefinition, variants: list[Variant]) -> TraitDetail:
    evaluation = evaluate_trait(trait, variants)
    rsids: list[TraitRsidDetail] = []
    observed_rsids = 0
    matched_rsids = 0

    for evaluated in evaluation.evaluated_rules:
        status: Literal["matched", "no_match", "missing"]
        if evaluated.user_genotype is None:
            meaning = "No genotype detected in uploaded data for this rsID."
            status = "missing"
        elif evaluated.interpretation is None:
            meaning = evaluated.rule.default_meaning or "No interpretation available."
            status = "no_match"
            observed_rsids += 1
        else:
            meaning = evaluated.interpretation.meaning
            status = "matched"
            observed_rsids += 1
            matched_rsids += 1

        effect = (
            evaluated.interpretation.effect
            if evaluated.interpretation and evaluated.interpretation.effect
            else evaluated.rule.effect or evaluated.rule.description
        )
        contribution = _contribution_from_interpretation(evaluated.interpretation)
        odds_ratio_note = _explain_odds_ratio(evaluated.rule.odds_ratio)
        contribution_explanation_parts = [
            _contribution_label(contribution, evaluation.result) + ".",
        ]
        if evaluated.interpretation is not None:
            contribution_explanation_parts.append(
                "Raw genotype score for this marker: "
                f"{evaluated.interpretation.score:.2f}."
            )
        if odds_ratio_note:
            contribution_explanation_parts.append(odds_ratio_note)

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
                status_explanation=_status_explanation(
                    evaluated.user_genotype, evaluated.interpretation
                ),
                contribution=contribution,
                contribution_label=_contribution_label(contribution, evaluation.result),
                contribution_explanation=" ".join(contribution_explanation_parts),
                weight=evaluated.rule.weight,
                evidence_level=evaluated.rule.evidence_level,
                source_refs=evaluated.rule.source_refs,
            )
        )

    total_rules = len(evaluation.evaluated_rules)
    missing_count = len(evaluation.missing_rsids)
    result_content = _get_result_content(evaluation.trait, evaluation.result)

    calculation_sections = [
        TraitContentSection(
            title="1. Marker lookup",
            body=(
                f"We checked {total_rules} curated marker"
                f"{'s' if total_rules != 1 else ''} for this trait and found "
                f"{observed_rsids} in your file, leaving {missing_count} "
                f"missing."
            ),
        ),
        TraitContentSection(
            title="2. Rule matching",
            body=(
                f"Each observed genotype was compared with the rule set for this "
                f"trait. {matched_rsids} marker"
                f"{'s' if matched_rsids != 1 else ''} matched a curated "
                "interpretation closely enough to contribute directional signal."
            ),
        ),
        TraitContentSection(
            title="3. Score formula",
            body=(
                "For every matched marker, we take the genotype score and multiply "
                "it by the marker weight. If an odds ratio is available, it also "
                "scales the signal through a logarithmic weighting step. The "
                f"weighted contributions are then normalized into the final trait "
                f"score of {evaluation.score:.2f}."
            ),
        ),
        TraitContentSection(
            title="4. Threshold decision",
            body=(
                "Scores greater than or equal to 0.25 become 'likely'. Scores "
                "less than or equal to -0.25 become 'unlikely'. Anything between "
                f"those thresholds stays 'inconclusive'. This trait landed at "
                f"{evaluation.score:.2f}."
            ),
        ),
        TraitContentSection(
            title="5. Confidence estimate",
            body=(
                "Confidence is not a probability of the trait. It is coverage "
                "multiplied by an evidence-strength modifier, so partial data or "
                f"weaker literature support lowers it. For this run that produced "  # noqa: E501
                f"{evaluation.confidence:.2f} confidence from {evaluation.coverage:.2f} "  # noqa: E501
                "coverage and the trait's evidence profile."
            ),
        ),
    ]
    calculation_sections.extend(evaluation.trait.calculation_notes)

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
        headline=result_content.headline,
        headline_tooltip=result_content.headline_tooltip,
        outcome_summary=result_content.outcome_summary,
        result_badge_tooltip=result_content.card_tooltip,
        practical_takeaway=(
            evaluation.trait.practical_takeaway
            or _fallback_practical_takeaway(evaluation.result)
        ),
        simple_explanation=(
            evaluation.trait.simple_explanation
            or _fallback_simple_explanation(evaluation.trait)
        ),
        technical_explanation=(
            evaluation.trait.technical_explanation
            or _fallback_technical_explanation(evaluation.trait)
        ),
        research_spotlight=(
            evaluation.trait.research_spotlight
            or _fallback_research_spotlight(evaluation.trait)
        ),
        calculation_summary=calculation_sections,
        rsids=rsids,
        sources=evaluation.trait.sources,
    )
