export type TraitCategory = 'nutrition' | 'appearance' | 'health' | 'behavior';

export type EvidenceLevel = 'strong' | 'moderate' | 'limited';

export type TraitResultLabel = 'likely' | 'unlikely' | 'inconclusive';

export type TraitSource = {
  name: string;
  url: string;
  reference?: string | null;
  notes?: string | null;
};

export type TraitResult = {
  trait_id: string;
  name: string;
  category: TraitCategory;
  missing_rsids: string[];
  matched_rsids: string[];
  confidence: number;
  result: TraitResultLabel;
  simple_summary: string;
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
  rsids: TraitRsidDetail[];
  sources: TraitSource[];
  notes: string[];
};
