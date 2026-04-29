export type TraitCategory = 'nutrition' | 'appearance' | 'health' | 'behavior';

export type EvidenceLevel = 'strong' | 'moderate' | 'limited';

export type TraitResultLabel = 'likely' | 'unlikely' | 'inconclusive';

export type TraitSource = {
  name: string;
  url: string;
  reference?: string | null;
  notes?: string | null;
};

export type TraitContentSection = {
  title: string;
  body: string;
};

export type TraitResult = {
  trait_id: string;
  name: string;
  category: TraitCategory;
  description: string;
  missing_rsids: string[];
  matched_rsids: string[];
  observed_rsids: string[];
  confidence: number;
  coverage: number;
  result: TraitResultLabel;
  simple_summary: string;
  user_summary: string;
  explanation_preview: string;
  result_badge_tooltip: string;
};

export type TraitRsidDetail = {
  rsid: string;
  genotype: string[] | null;
  user_genotype: string[] | null;
  gene?: string | null;
  effect?: string | null;
  odds_ratio?: number | null;
  score?: number | null;
  meaning: string;
  rule_description: string;
  status: 'matched' | 'no_match' | 'missing';
  status_explanation: string;
  contribution: 'raises' | 'lowers' | 'neutral' | 'unknown';
  contribution_label: string;
  contribution_explanation: string;
  weight: number;
  evidence_level?: EvidenceLevel | null;
  source_refs: string[];
};

export type TraitDetail = {
  id: string;
  name: string;
  category: TraitCategory;
  result: TraitResultLabel;
  confidence: number;
  description: string;
  simple_summary: string;
  technical_summary: string;
  evidence_level: EvidenceLevel;
  keywords: string[];
  coverage: number;
  score: number;
  headline: string;
  headline_tooltip: string;
  outcome_summary: string;
  result_badge_tooltip: string;
  practical_takeaway: TraitContentSection[];
  simple_explanation: TraitContentSection[];
  technical_explanation: TraitContentSection[];
  research_spotlight: TraitContentSection[];
  calculation_summary: TraitContentSection[];
  rsids: TraitRsidDetail[];
  sources: TraitSource[];
};
