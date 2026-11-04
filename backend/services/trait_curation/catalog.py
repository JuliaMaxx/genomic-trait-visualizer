import json
import math
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from backend.models import (
    AnalysisOutcome,
    ContentSection,
    ContributionDirection,
    CuratedTraitRule,
    EvaluatedRule,
    EvidenceLevel,
    GenotypeInterpretation,
    RsidCatalogItem,
    RsidDetail,
    RsidTraitLink,
    SearchResponse,
    SearchResult,
    TraitAnalysisDetail,
    TraitAnalysisMetrics,
    TraitAnalysisSummary,
    TraitCatalog,
    TraitCatalogDetail,
    TraitCatalogSummary,
    TraitDefinition,
    TraitEvaluation,
    TraitResultContent,
    TraitRuleAnalysis,
    TraitRuleStatus,
    TraitSource,
    Variant,
)
from backend.models.common import TraitCategory

CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "traits.json"


@lru_cache(maxsize=1)
def load_trait_catalog() -> TraitCatalog:
    with CATALOG_PATH.open("r", encoding="utf-8") as catalog_file:
        return TraitCatalog.model_validate(json.load(catalog_file))


@lru_cache(maxsize=1)
def _trait_lookup_by_id() -> dict[str, TraitDefinition]:
    return {trait.id: trait for trait in load_trait_catalog().traits}


def list_trait_definitions() -> list[TraitDefinition]:
    return list(load_trait_catalog().traits)


def get_trait_definition(trait_id: str) -> TraitDefinition | None:
    return _trait_lookup_by_id().get(trait_id)


def list_trait_summaries() -> list[TraitCatalogSummary]:
    return [
        TraitCatalogSummary(
            id=trait.id,
            name=trait.name,
            category=trait.category,
            description=trait.description,
            simple_summary=trait.simple_summary,
            technical_summary=trait.technical_summary,
            evidence_level=trait.evidence_level,
            keywords=trait.keywords,
            search_terms=_trait_search_terms(trait),
        )
        for trait in list_trait_definitions()
    ]


def _trait_search_terms(trait: TraitDefinition) -> list[str]:
    terms: list[str] = []
    for rule in trait.rules:
        terms.extend([rule.rsid, rule.gene, rule.description])
        for meaning in rule.genotype_meanings:
            terms.extend(meaning.genotype)
            terms.extend([meaning.meaning, meaning.effect])
    return terms


def trait_catalog_detail(trait: TraitDefinition) -> TraitCatalogDetail:
    return TraitCatalogDetail.model_validate(trait.model_dump())


def _evidence_rank(level: str | None) -> int:
    return {"limited": 1, "moderate": 2, "strong": 3}.get(level or "", 0)


def _strongest_evidence(levels: list[EvidenceLevel | None]) -> EvidenceLevel | None:
    available = [level for level in levels if level is not None]
    return max(available, key=_evidence_rank) if available else None


def _sources_for_ref(
    trait: TraitDefinition, ref: str, rule: CuratedTraitRule
) -> list[TraitSource]:
    matches = [source for source in trait.sources if source.name == ref]
    exact_matches = [source for source in matches if rule.rsid in source.reference]
    return exact_matches or matches


def _rule_effect(rule: CuratedTraitRule) -> str:
    effects = [
        f"{' or '.join(meaning.genotype)}: {meaning.effect}"
        for meaning in rule.genotype_meanings
    ]
    return "; ".join(effects)


def _plain_rsid_summary(rsid: str, links: list[RsidTraitLink], gene: str | None) -> str:
    trait_names = ", ".join(link.trait_name for link in links[:2])
    extra = len(links) - 2
    trait_text = trait_names if extra <= 0 else f"{trait_names}, and {extra} more"
    gene_text = f" near or in {gene}" if gene else ""
    return (
        f"{rsid}{gene_text} appears in curated rules connected to {trait_text}. "
        "Its effect varies by genotype and research context."
    )


def _technical_rsid_summary(
    rsid: str,
    rules: list[CuratedTraitRule],
    links: list[RsidTraitLink],
    gene: str | None,
) -> str:
    genotype_count = sum(len(rule.genotype_meanings) for rule in rules)
    evidence = _strongest_evidence([link.evidence_level for link in links])
    if gene is not None:
        gene_text = gene
    else:
        genes = {rule.gene for rule in rules}
        gene_text = "multiple genes" if len(genes) > 1 else "an unspecified region"
    return (
        f"{rsid} is represented by {len(rules)} curated rule"
        f"{'s' if len(rules) != 1 else ''} mapped to {gene_text}. "
        f"The catalog recognizes {genotype_count} genotype interpretation"
        f"{'s' if genotype_count != 1 else ''} and links the marker to "
        f"{len(links)} trait model{'s' if len(links) != 1 else ''}. "
        f"The strongest linked evidence level is {evidence or 'ungraded'}."
    )


def _rsid_story_sections(
    rsid: str, links: list[RsidTraitLink], rules: list[CuratedTraitRule]
) -> list[ContentSection]:
    linked_traits = ", ".join(link.trait_name for link in links)
    source_refs = sorted({ref for rule in rules for ref in rule.source_refs})
    return [
        ContentSection(
            title="Why this marker is here",
            body=(
                f"{rsid} appears because curated trait models use it as one signal "
                f"for {linked_traits or 'a trait pathway'}. A single SNP rarely "
                "explains a whole trait; here it is one part of an "
                "educational rule set."
            ),
        ),
        ContentSection(
            title="What the catalog is saying",
            body=(
                "The catalog stores genotype-level associations, not destiny. "
                "Genotypes can point in different directions, and ancestry, "
                "environment, measurement, or other variants can affect how well "
                "an association applies."
            ),
        ),
        ContentSection(
            title="Where the evidence comes from",
            body=f"The linked source labels are {', '.join(source_refs)}.",
        ),
    ]


def _rsid_interpretation_notes(
    rules: list[CuratedTraitRule], meanings: list[GenotypeInterpretation]
) -> list[ContentSection]:
    positive = sum(meaning.score > 0 for meaning in meanings)
    negative = sum(meaning.score < 0 for meaning in meanings)
    neutral = sum(meaning.score == 0 for meaning in meanings)
    notes = [
        ContentSection(
            title="Score direction",
            body=(
                f"This marker has {positive} positive, {negative} negative, and "
                f"{neutral} neutral genotype score{'s' if len(meanings) != 1 else ''}."
            ),
        ),
        ContentSection(
            title="How it enters a trait model",
            body=(
                "A matching genotype contributes to the linked trait score. An "
                "observed genotype without a matching interpretation does not add "
                "directional signal."
            ),
        ),
    ]
    if any(rule.weight != 1 or rule.odds_ratio is not None for rule in rules):
        notes.append(
            ContentSection(
                title="Association weighting",
                body=(
                    "At least one linked rule uses a non-default weight or a "
                    "reported odds ratio. These are model inputs, not personal "
                    "probabilities."
                ),
            )
        )
    return notes


def _rsid_links(rsid: str) -> tuple[list[RsidTraitLink], list[TraitSource]]:
    links: list[RsidTraitLink] = []
    sources: list[TraitSource] = []
    seen_source_urls: set[str] = set()

    for trait in list_trait_definitions():
        for rule in trait.rules:
            if rule.rsid != rsid:
                continue
            links.append(
                RsidTraitLink(
                    trait_id=trait.id,
                    trait_name=trait.name,
                    category=trait.category,
                    description=rule.description,
                    effect=_rule_effect(rule),
                    evidence_level=rule.evidence_level,
                    source_refs=rule.source_refs,
                )
            )
            for ref in rule.source_refs:
                for source in _sources_for_ref(trait, ref, rule):
                    source_url = str(source.url)
                    if source_url not in seen_source_urls:
                        sources.append(source)
                        seen_source_urls.add(source_url)
    return links, sources


def _genes_for_rsid(rsid: str) -> list[str]:
    return list(
        dict.fromkeys(
            rule.gene
            for trait in list_trait_definitions()
            for rule in trait.rules
            if rule.rsid == rsid
        )
    )


def list_rsid_catalog() -> list[RsidCatalogItem]:
    rsids = sorted(
        {rule.rsid for trait in list_trait_definitions() for rule in trait.rules}
    )
    items: list[RsidCatalogItem] = []
    for rsid in rsids:
        links, _ = _rsid_links(rsid)
        genes = _genes_for_rsid(rsid)
        gene = genes[0] if len(genes) == 1 else None
        items.append(
            RsidCatalogItem(
                rsid=rsid,
                gene=gene,
                plain_english_summary=_plain_rsid_summary(rsid, links, gene),
                trait_count=len({link.trait_id for link in links}),
                evidence_level=_strongest_evidence(
                    [link.evidence_level for link in links]
                ),
            )
        )
    return items


def get_rsid_detail(rsid: str) -> RsidDetail | None:
    matching = [
        rule
        for trait in list_trait_definitions()
        for rule in trait.rules
        if rule.rsid.lower() == rsid.lower()
    ]
    if not matching:
        return None

    canonical_rsid = matching[0].rsid
    links, sources = _rsid_links(canonical_rsid)
    genes = _genes_for_rsid(canonical_rsid)
    gene = genes[0] if len(genes) == 1 else None
    meanings: list[GenotypeInterpretation] = []
    for rule in matching:
        for meaning in rule.genotype_meanings:
            if meaning not in meanings:
                meanings.append(meaning)
    effects = list(dict.fromkeys(meaning.effect for meaning in meanings))
    descriptions = list(dict.fromkeys(rule.description for rule in matching))

    return RsidDetail(
        rsid=canonical_rsid,
        gene=gene,
        plain_english_summary=_plain_rsid_summary(canonical_rsid, links, gene),
        technical_summary=_technical_rsid_summary(
            canonical_rsid, matching, links, gene
        ),
        description=" ".join(descriptions),
        genotype_meanings=meanings,
        effect_directions=effects,
        traits=links,
        story_sections=_rsid_story_sections(canonical_rsid, links, matching),
        interpretation_notes=_rsid_interpretation_notes(matching, meanings),
        sources=sources,
    )


def _search_text_matches(query: str, values: Sequence[str | None]) -> bool:
    tokens = [token for token in query.strip().lower().split() if token]
    searchable = " ".join(value for value in values if value).lower()
    return all(token in searchable for token in tokens)


def search_catalog(
    query: str,
    category: TraitCategory | None = None,
    evidence_level: EvidenceLevel | None = None,
    limit: int = 8,
) -> SearchResponse:
    normalized_category = category.strip().lower() if category else None
    normalized_evidence = evidence_level.strip().lower() if evidence_level else None
    results: list[SearchResult] = []

    for trait in list_trait_definitions():
        if normalized_category and trait.category != normalized_category:
            continue
        if normalized_evidence and trait.evidence_level != normalized_evidence:
            continue
        searchable = [
            trait.id,
            trait.name,
            trait.category,
            trait.description,
            trait.simple_summary,
            trait.technical_summary,
            " ".join(trait.keywords),
            " ".join(rule.rsid for rule in trait.rules),
            " ".join(rule.gene for rule in trait.rules),
            " ".join(rule.description for rule in trait.rules),
        ]
        if _search_text_matches(query, searchable):
            results.append(
                SearchResult(
                    kind="trait",
                    title=trait.name,
                    subtitle=trait.category,
                    description=trait.simple_summary,
                    url=f"/traits/{trait.id}",
                )
            )

    for item in list_rsid_catalog():
        if normalized_evidence and item.evidence_level != normalized_evidence:
            continue
        detail = get_rsid_detail(item.rsid)
        links = detail.traits if detail else []
        if normalized_category and not any(
            link.category == normalized_category for link in links
        ):
            continue
        if _search_text_matches(
            query,
            [
                item.rsid,
                item.gene,
                item.plain_english_summary,
                " ".join(link.trait_name for link in links),
                " ".join(link.description for link in links),
                " ".join(link.effect for link in links),
            ],
        ):
            results.append(
                SearchResult(
                    kind="rsid",
                    title=item.rsid,
                    subtitle=item.gene or "genetic marker",
                    description=item.plain_english_summary,
                    url=f"/rsids/{item.rsid}",
                )
            )
    return SearchResponse(query=query, results=results[:limit])


def _normalize_genotype(genotype: str | list[str]) -> str:
    value = "".join(genotype) if isinstance(genotype, list) else genotype
    value = value.replace(" ", "").replace("/", "").upper()
    return "".join(sorted(value)) if len(value) == 2 else value


def _normalize_genotype_alleles(genotype: str | list[str]) -> list[str]:
    if isinstance(genotype, list):
        return [allele.strip().upper() for allele in genotype if allele.strip()]
    return list(_normalize_genotype(genotype))


def _normalize_genotypes(genotypes: list[str]) -> set[str]:
    return {_normalize_genotype(genotype) for genotype in genotypes}


def _find_interpretation(
    rule: CuratedTraitRule, user_genotype: str
) -> GenotypeInterpretation | None:
    for interpretation in sorted(
        rule.genotype_meanings, key=lambda entry: abs(entry.score), reverse=True
    ):
        if user_genotype in _normalize_genotypes(interpretation.genotype):
            return interpretation
    return None


def _interpretation_weight(
    rule: CuratedTraitRule, interpretation: GenotypeInterpretation
) -> float:
    direction = 1 if interpretation.score > 0 else -1 if interpretation.score < 0 else 0
    if direction == 0:
        return 0.0
    score_hint = abs(interpretation.score)
    if rule.odds_ratio is not None:
        return direction * score_hint * math.log(rule.odds_ratio)
    return direction * score_hint


def _result_from_score(score: float) -> AnalysisOutcome:
    if score >= 0.25:
        return "likely"
    if score <= -0.25:
        return "unlikely"
    return "inconclusive"


def _evidence_modifier(
    trait: TraitDefinition, evaluated_rules: list[EvaluatedRule]
) -> float:
    signals = [
        abs(_interpretation_weight(entry.rule, entry.interpretation))
        for entry in evaluated_rules
        if entry.interpretation is not None
    ]
    if not signals:
        return 0.0
    mean_signal = sum(signals) / len(signals)
    level_bonus = {"strong": 1.0, "moderate": 0.8, "limited": 0.6}[trait.evidence_level]
    return min(1.0, mean_signal * level_bonus)


def evaluate_trait(trait: TraitDefinition, variants: list[Variant]) -> TraitEvaluation:
    variant_lookup = {variant.rsid: variant for variant in variants}
    evaluated_rules: list[EvaluatedRule] = []
    total_weight = sum(rule.weight for rule in trait.rules)
    observed_weight = 0.0
    weighted_score_sum = 0.0

    for rule in sorted(trait.rules, key=lambda entry: entry.priority):
        variant = variant_lookup.get(rule.rsid)
        if variant is None or not variant.genotype:
            evaluated_rules.append(
                EvaluatedRule(rule=rule, user_genotype=None, interpretation=None)
            )
            continue

        genotype_alleles = _normalize_genotype_alleles(variant.genotype)
        user_genotype = _normalize_genotype(genotype_alleles)
        observed_weight += rule.weight
        interpretation = _find_interpretation(rule, user_genotype)
        if interpretation is not None:
            weighted_score_sum += rule.weight * _interpretation_weight(
                rule, interpretation
            )
        evaluated_rules.append(
            EvaluatedRule(
                rule=rule,
                user_genotype=genotype_alleles,
                interpretation=interpretation,
            )
        )

    coverage = observed_weight / total_weight
    has_matched_genotype = any(entry.status == "matched" for entry in evaluated_rules)
    score = weighted_score_sum / total_weight if has_matched_genotype else None
    result = _result_from_score(score if score is not None else 0.0)
    confidence = coverage * _evidence_modifier(trait, evaluated_rules)
    return TraitEvaluation(
        trait=trait,
        evaluated_rules=evaluated_rules,
        coverage=coverage,
        confidence=confidence,
        score=score,
        result=result,
    )


def build_trait_result(evaluation: TraitEvaluation) -> TraitAnalysisSummary:
    return TraitAnalysisSummary(
        trait_id=evaluation.trait.id,
        name=evaluation.trait.name,
        category=evaluation.trait.category,
        description=evaluation.trait.description,
        rule_statuses=[
            TraitRuleStatus(rsid=entry.rule.rsid, status=entry.status)
            for entry in evaluation.evaluated_rules
        ],
        confidence=evaluation.confidence,
        coverage=evaluation.coverage,
        result=evaluation.result,
        result_badge_tooltip=_analysis_result_content(evaluation).card_tooltip,
    )


def _analysis_result_content(evaluation: TraitEvaluation) -> TraitResultContent:
    if evaluation.matched_rsids:
        content_by_result = {
            "likely": evaluation.trait.result_content.likely,
            "unlikely": evaluation.trait.result_content.unlikely,
            "inconclusive": evaluation.trait.result_content.inconclusive,
        }
        return content_by_result[evaluation.result]
    if evaluation.observed_rsids:
        return TraitResultContent(
            card_tooltip=(
                "The uploaded file contained genotypes, but none matched an "
                "interpretation in this trait's catalog rules."
            ),
            headline=(
                "No catalog interpretation matched for "
                f"{evaluation.trait.name.lower()}."
            ),
            headline_tooltip=(
                "The file contained genotype data, but none of the observed patterns "
                "matched a published interpretation for this trait."
            ),
            outcome_summary=(
                "The result is inconclusive because none of the observed genotypes "
                "matched a published interpretation for this trait."
            ),
        )
    return TraitResultContent(
        card_tooltip=(
            f"No usable genotype for {evaluation.trait.name.lower()} was found in "
            "the uploaded DNA data."
        ),
        headline=(
            f"There is not enough DNA data to assess {evaluation.trait.name.lower()}."
        ),
        headline_tooltip=(
            "The available file did not contain a usable genotype for this "
            "trait's rules."
        ),
        outcome_summary=(
            "The result is inconclusive because no usable genotype was available "
            "for this trait's catalog rules."
        ),
    )


def _format_genotype(genotype: list[str] | None) -> str:
    return "".join(genotype) if genotype else "not available"


def _status_explanation(entry: EvaluatedRule) -> str:
    if entry.status == "missing":
        return (
            "This marker is part of the model, but the upload did not contain a "
            "usable genotype for it."
        )
    if entry.status == "unmatched":
        return (
            f"The upload contains genotype {_format_genotype(entry.user_genotype)}, "
            "but no curated interpretation matches it."
        )
    return (
        f"The observed genotype {_format_genotype(entry.user_genotype)} matches "
        "a curated genotype interpretation."
    )


def _contribution(entry: EvaluatedRule) -> ContributionDirection:
    if entry.interpretation is None:
        return "unknown"
    if entry.interpretation.score > 0:
        return "raises"
    if entry.interpretation.score < 0:
        return "lowers"
    return "neutral"


def _contribution_label(direction: str) -> str:
    return {
        "raises": "Pushes the trait toward a likely result",
        "lowers": "Pushes the trait away from a likely result",
        "neutral": "Adds no directional score",
        "unknown": "Could not be used in the final call",
    }[direction]


def _contribution_explanation(entry: EvaluatedRule) -> str:
    direction = _contribution(entry)
    parts = [_contribution_label(direction) + "."]
    if entry.interpretation is not None:
        parts.append(f"Genotype score: {entry.interpretation.score:.2f}.")
    if entry.rule.odds_ratio is not None:
        parts.append(
            f"Reported odds ratio: {entry.rule.odds_ratio:.2f}; this is a research "
            "association statistic, not a personal probability."
        )
    return " ".join(parts)


def _calculation_explanation(evaluation: TraitEvaluation) -> list[ContentSection]:
    rules = evaluation.evaluated_rules
    observed = len(evaluation.observed_rsids)
    matched = len(evaluation.matched_rsids)
    missing = len(evaluation.missing_rsids)
    observed_markers = f"{observed} marker{'s' if observed != 1 else ''}"
    missing_markers = f"{missing} marker{'s' if missing != 1 else ''}"
    sections = [
        ContentSection(
            title="1. Marker lookup",
            body=(
                f"We checked {len(rules)} curated marker rules. Genotype data was "
                f"present for {observed_markers}; {missing_markers} had none."
            ),
        ),
        ContentSection(
            title="2. Rule matching",
            body=(
                f"{matched} observed genotype{'s' if matched != 1 else ''} matched "
                "a curated interpretation. Observed genotypes without a match do not "
                "contribute a directional score."
            ),
        ),
    ]
    if evaluation.score is None and evaluation.observed_rsids:
        sections.append(
            ContentSection(
                title="3. Score",
                body=(
                    "Genotype data was present, but none of the observed patterns "
                    "matched a published interpretation. The directional score is "
                    "unavailable."
                ),
            )
        )
    elif evaluation.score is None:
        sections.append(
            ContentSection(
                title="3. Score",
                body=(
                    "No genotype data was found for this trait's marker rules, so "
                    "the directional score is unavailable."
                ),
            )
        )
    else:
        sections.append(
            ContentSection(
                title="3. Score",
                body=(
                    "For each matched genotype, the model scales its score by the "
                    "natural logarithm (ln) of the reported odds ratio when one is "
                    "available, then applies that rule's weight. It divides the "
                    "weighted contributions by the total weight of all trait rules. "
                    f"This run's score is {evaluation.score:.2f}."
                ),
            )
        )
    sections.extend(
        [
            ContentSection(
                title="4. Result label",
                body=(
                    "Scores at or above 0.25 are labeled likely; scores at or below "
                    "-0.25 are labeled unlikely; other scores are inconclusive. "
                    f"This run is {evaluation.result}."
                ),
            ),
            ContentSection(
                title="5. Confidence and coverage",
                body=(
                    "Coverage is the fraction of total rule weight for which "
                    "genotype data was available. "
                    "Confidence combines coverage with the model's evidence modifier; "
                    f"this run has {evaluation.coverage:.2f} coverage and "
                    f"{evaluation.confidence:.2f} confidence. Neither is a probability."
                ),
            ),
        ]
    )
    sections.extend(evaluation.trait.calculation_notes)
    return sections


def build_trait_detail(
    trait: TraitDefinition, variants: list[Variant]
) -> TraitAnalysisDetail:
    evaluation = evaluate_trait(trait, variants)
    rule_results = [
        TraitRuleAnalysis(
            rsid=entry.rule.rsid,
            user_genotype=entry.user_genotype,
            interpretation=entry.interpretation,
            status=entry.status,
            status_explanation=_status_explanation(entry),
            contribution=_contribution(entry),
            contribution_label=_contribution_label(_contribution(entry)),
            contribution_explanation=_contribution_explanation(entry),
        )
        for entry in evaluation.evaluated_rules
    ]
    return TraitAnalysisDetail(
        trait=trait_catalog_detail(evaluation.trait),
        analysis=TraitAnalysisMetrics(
            result=evaluation.result,
            confidence=evaluation.confidence,
            coverage=evaluation.coverage,
            score=evaluation.score,
            result_content=_analysis_result_content(evaluation),
            rules=rule_results,
            calculation_explanation=_calculation_explanation(evaluation),
        ),
    )
