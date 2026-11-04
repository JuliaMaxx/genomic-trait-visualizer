import { Link } from 'react-router-dom';
import type {
  CuratedTraitRule,
  TraitRuleAnalysis,
} from '../types/api';
import { formatEvidenceLabel } from '../utils/formatLabels';
import StatPill from './StatPill';

type Props = {
  analysis: TraitRuleAnalysis;
  rule: CuratedTraitRule;
};

const statusLabels: Record<TraitRuleAnalysis['status'], string> = {
  matched: 'Matched rule',
  unmatched: 'Observed only',
  missing: 'Missing',
};

function matchTone(status: string) {
  if (status === 'matched') {
    return 'ui-badge-success';
  }
  if (status === 'missing') {
    return 'ui-badge-warning';
  }
  return 'ui-badge-danger';
}

const contributionTone: Record<
  TraitRuleAnalysis['contribution'],
  'default' | 'accent'
> = {
  raises: 'accent',
  lowers: 'default',
  neutral: 'default',
  unknown: 'default',
};

function formatGenotype(genotype: string[] | null) {
  if (!genotype || genotype.length === 0) {
    return 'Not available';
  }

  return genotype.join('');
}

function TraitDetailRsidCard({ analysis, rule }: Props) {
  const knownGenotypes = rule.genotype_meanings.flatMap(
    (meaning) => meaning.genotype,
  );
  const meaning =
    analysis.interpretation?.meaning ??
    (analysis.status === 'missing'
      ? 'No genotype was available to interpret.'
      : 'The observed genotype has no matching catalog interpretation.');

  return (
    <Link to={`/rsids/${analysis.rsid}`}>
      <article className="ui-card-link">
        <div className="flex flex-wrap items-center justify-between gap-md">
          <div>
            <div className="flex items-center gap-sm">
              <div className="ui-paragraph-subtle">{analysis.rsid}</div>
              <span className={`ui-result-badge ${matchTone(analysis.status)}`}>
                {statusLabels[analysis.status]}
              </span>
            </div>
            <h3 className="ui-paragraph-strong mt-2xs">
              {rule.gene}
            </h3>
          </div>
          <div className="flex flex-wrap gap-sm">
            <StatPill
              label="Your genotype"
              value={formatGenotype(analysis.user_genotype)}
              tooltip="This is the genotype found in your uploaded DNA file for this rsID."
            />
            {knownGenotypes.length > 0 ? (
              <StatPill
                label="Known genotypes"
                value={knownGenotypes.join(', ')}
                tooltip="These are the genotype patterns that the current educational rule set knows how to interpret for this rsID."
              />
            ) : null}
          </div>
        </div>

        <div className="mt-md grid gap-md lg:grid-cols-2">
          <div className="ui-panel-subtle">
            <p className="ui-eyebrow">what this marker is</p>
            <p className="ui-item-title-subtle">{rule.description}</p>
            <p className="ui-item-body-faint">{analysis.status_explanation}</p>
          </div>

          <div className="ui-panel-accent">
            <p className="ui-eyebrow-accent">what your genotype means</p>
            <p className="ui-item-title-subtle">{meaning}</p>
            <p className="ui-item-body-faint">
              {analysis.contribution_explanation}
            </p>
          </div>
        </div>

        <div className="ui-pill-collection">
          {analysis.interpretation?.effect ? (
            <StatPill
              label="Effect"
              value={analysis.interpretation.effect}
              tone="accent"
              tooltip="This is the direction this rsID is associated with in the curated rule set."
            />
          ) : null}
          <StatPill
            label="Contribution"
            value={analysis.contribution_label}
            tone={contributionTone[analysis.contribution]}
            tooltip="Contribution explains how this rsID pushed the overall trait result, if it could be interpreted."
          />
          <StatPill
            label="Odds ratio"
            value={
              rule.odds_ratio === null
                ? rule.odds_ratio_status === 'not_applicable'
                  ? 'Not applicable'
                  : 'Not reported'
                : rule.odds_ratio.toFixed(2)
            }
            tooltip="Odds ratios are research association statistics, not direct probabilities for you personally. The catalog distinguishes unreported values from values that do not apply."
          />
          {analysis.interpretation ? (
            <StatPill
              label="Genotype score"
              value={analysis.interpretation.score.toFixed(2)}
              tooltip="This is the directional score assigned to your genotype for this rsID before the model combines it with other rsIDs."
            />
          ) : null}
          <StatPill
            label="Weight"
            value={rule.weight.toFixed(2)}
            tooltip="Weight tells you how much influence this rsID has inside the current simplified trait model."
          />
          <StatPill
            label="Evidence"
            value={formatEvidenceLabel(rule.evidence_level)}
            tooltip="Evidence level describes how strong the supporting curated research is for this rsID rule."
          />
        </div>
      </article>
    </Link>
  );
}

export default TraitDetailRsidCard;
