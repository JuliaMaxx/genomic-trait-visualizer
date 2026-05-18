import type {
  EvidenceLevel,
  RsidCatalogItem,
  TraitCategory,
  TraitDefinition,
  TraitResult,
  TraitResultLabel,
} from '../types/analysis';

export type ConfidenceBand = 'high' | 'medium' | 'low';

export type AnalysisFilters = {
  query: string;
  likelihood: TraitResultLabel | 'all';
  confidence: ConfidenceBand | 'all';
  category: TraitCategory | 'all';
};

export type TraitCatalogFilters = {
  query: string;
  category: TraitCategory | 'all';
  evidence: EvidenceLevel | 'all';
};

export type RsidCatalogFilters = {
  query: string;
  evidence: EvidenceLevel | 'all';
};

function normalize(value: string) {
  return value.trim().toLowerCase();
}

function matchesQuery(query: string, values: (string | null | undefined)[]) {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  if (tokens.length === 0) {
    return true;
  }

  const haystack = values.filter(Boolean).join(' ').toLowerCase();
  return tokens.every((token) => haystack.includes(token));
}

export function getConfidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= 0.75) {
    return 'high';
  }

  if (confidence >= 0.4) {
    return 'medium';
  }

  return 'low';
}

export function filterAnalysisTraits(
  traits: TraitResult[],
  filters: AnalysisFilters,
) {
  return traits.filter((trait) => {
    if (trait.observed_rsids.length === 0) {
      return false;
    }

    if (filters.likelihood !== 'all' && trait.result !== filters.likelihood) {
      return false;
    }

    if (filters.category !== 'all' && trait.category !== filters.category) {
      return false;
    }

    if (
      filters.confidence !== 'all' &&
      getConfidenceBand(trait.confidence) !== filters.confidence
    ) {
      return false;
    }

    return matchesQuery(filters.query, [
      trait.trait_id,
      trait.name,
      trait.category,
      trait.description,
      trait.simple_summary,
      trait.user_summary,
      trait.explanation_preview,
      trait.result,
      ...trait.matched_rsids,
      ...trait.observed_rsids,
    ]);
  });
}

export function filterTraitCatalog(
  traits: TraitDefinition[],
  filters: TraitCatalogFilters,
) {
  return traits.filter((trait) => {
    if (filters.category !== 'all' && trait.category !== filters.category) {
      return false;
    }

    if (filters.evidence !== 'all' && trait.evidence_level !== filters.evidence) {
      return false;
    }

    return matchesQuery(filters.query, [
      trait.id,
      trait.name,
      trait.category,
      trait.description,
      trait.simple_summary,
      trait.technical_summary,
      trait.evidence_level,
      ...trait.keywords,
      ...(trait.rules?.map((rule) => rule.rsid) ?? []),
      ...(trait.rules?.map((rule) => rule.gene) ?? []),
      ...(trait.rules?.map((rule) => rule.description) ?? []),
      ...(trait.rules?.map((rule) => rule.effect) ?? []),
    ]);
  });
}

export function filterRsidCatalog(
  rsids: RsidCatalogItem[],
  filters: RsidCatalogFilters,
) {
  return rsids.filter((rsid) => {
    if (
      filters.evidence !== 'all' &&
      rsid.evidence_level !== filters.evidence
    ) {
      return false;
    }

    return matchesQuery(filters.query, [
      rsid.rsid,
      rsid.gene,
      rsid.plain_english_summary,
      rsid.evidence_level,
    ]);
  });
}
