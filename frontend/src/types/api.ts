import type { components } from './generated-api';

// These aliases point to OpenAPI-generated schemas; contract fields live in FastAPI.
export type TraitCategory =
  components['schemas']['TraitCatalogSummary']['category'];
export type EvidenceLevel =
  components['schemas']['TraitCatalogSummary']['evidence_level'];
export type TraitResultLabel =
  components['schemas']['TraitAnalysisSummary']['result'];
export type TraitSource = components['schemas']['TraitSource'];
export type CuratedTraitRule = components['schemas']['CuratedTraitRule'];
export type TraitCatalogSummary = components['schemas']['TraitCatalogSummary'];
export type TraitCatalogDetail = components['schemas']['TraitCatalogDetail'];
export type TraitAnalysisSummary =
  components['schemas']['TraitAnalysisSummary'];
export type TraitRuleAnalysis = components['schemas']['TraitRuleAnalysis'];
export type TraitAnalysisDetail = components['schemas']['TraitAnalysisDetail'];
export type RsidCatalogItem = components['schemas']['RsidCatalogItem'];
export type RsidDetail = components['schemas']['RsidDetail'];
export type SearchResult = components['schemas']['SearchResult'];
export type SearchResponse = components['schemas']['SearchResponse'];
