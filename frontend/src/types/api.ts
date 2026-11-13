import type { components } from './generated-api';

// Stage 7 contract aliases. The legacy React presentation is migrated in Stage 8.
export type TraitCategory =
  components['schemas']['TraitCatalogSummary']['category'];
export type EvidenceLevel = NonNullable<
  components['schemas']['RsidCatalogItem']['evidence_level']
>;
export type InterpretationStatus =
  components['schemas']['TraitAnalysisSummary']['status'];
export type InterpretationStrategy =
  components['schemas']['TraitCatalogSummary']['strategy'];
export type TraitSource = components['schemas']['EvidenceSource'];
export type PublishedClaim = components['schemas']['PublishedClaim'];
export type ExplanationText = components['schemas']['ExplanationText'];
export type TraitCatalogSummary = components['schemas']['TraitCatalogSummary'];
export type TraitCatalogDetail = components['schemas']['TraitCatalogDetail'];
export type TraitAnalysisSummary =
  components['schemas']['TraitAnalysisSummary'];
export type TraitAnalysisMetrics = components['schemas']['TraitAnalysisMetrics'];
export type TraitAnalysisDetail = components['schemas']['TraitAnalysisDetail'];
export type RsidCatalogItem = components['schemas']['RsidCatalogItem'];
export type RsidDetail = components['schemas']['RsidDetail'];
export type SearchResult = components['schemas']['SearchResult'];
export type SearchResponse = components['schemas']['SearchResponse'];
