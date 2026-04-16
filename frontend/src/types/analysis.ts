type TraitRule = {
  rsid: string;
  genotype: string | string[];
  odds_ratio?: number | null;
  beta?: number | null;
  description: string;
};

type Trait = {
  trait_id: string;
  name: string;

  matched_rules: TraitRule[];
  missing_rsids: string[];

  confidence: number;

  notes: string[];
};
