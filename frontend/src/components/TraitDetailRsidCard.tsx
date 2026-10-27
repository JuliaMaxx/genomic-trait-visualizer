import { Link } from 'react-router-dom';
import type { TraitRsidDetail } from '../types/analysis';
import { formatEvidenceLabel } from '../utils/formatLabels';
import StatPill from './StatPill';

type Props = {
  rsid: TraitRsidDetail;
};

const statusLabels: Record<TraitRsidDetail['status'], string> = {
  matched: 'Matched rule',
  no_match: 'Observed only',
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
  TraitRsidDetail['contribution'],
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

function TraitDetailRsidCard({ rsid }: Props) {
  return (
    <Link to={`/rsids/${rsid.rsid}`}>
      <article className="ui-card-link">
        <div className="flex flex-wrap items-center justify-between gap-md">
          <div>
            <div className="flex items-center gap-sm">
              <div className="ui-paragraph-subtle">{rsid.rsid}</div>
              <span className={`ui-result-badge ${matchTone(rsid.status)}`}>
                {statusLabels[rsid.status]}
              </span>
            </div>
            <h3 className="ui-paragraph-strong mt-2xs">
              {rsid.gene ?? 'Genetic marker'}
            </h3>
          </div>
          <div className="flex flex-wrap gap-sm">
            <StatPill
              label="Your genotype"
              value={formatGenotype(rsid.user_genotype)}
              tooltip="This is the genotype found in your uploaded DNA file for this rsID."
            />
            {rsid.genotype ? (
              <StatPill
                label="Known genotypes"
                value={rsid.genotype.join(', ')}
                tooltip="These are the genotype patterns that the current educational rule set knows how to interpret for this rsID."
              />
            ) : null}
          </div>
        </div>

        <div className="mt-md grid gap-md lg:grid-cols-2">
          <div className="ui-panel-subtle">
            <p className="ui-eyebrow">what this marker is</p>
            <p className="ui-item-title-subtle">{rsid.rule_description}</p>
            <p className="ui-item-body-faint">{rsid.status_explanation}</p>
          </div>

          <div className="ui-panel-accent">
            <p className="ui-eyebrow-accent">what your genotype means</p>
            <p className="ui-item-title-subtle">{rsid.meaning}</p>
            <p className="ui-item-body-faint">
              {rsid.contribution_explanation}
            </p>
          </div>
        </div>

        <div className="ui-pill-collection">
          {rsid.effect ? (
            <StatPill
              label="Effect"
              value={rsid.effect}
              tone="accent"
              tooltip="This is the direction this rsID is associated with in the curated rule set."
            />
          ) : null}
          <StatPill
            label="Contribution"
            value={rsid.contribution_label}
            tone={contributionTone[rsid.contribution]}
            tooltip="Contribution explains how this rsID pushed the overall trait result, if it could be interpreted."
          />
          {rsid.odds_ratio ? (
            <StatPill
              label="Odds ratio"
              value={rsid.odds_ratio.toFixed(2)}
              tooltip="Odds ratio is a research statistic showing association strength. It is not a direct probability for you personally."
            />
          ) : null}
          {typeof rsid.score === 'number' ? (
            <StatPill
              label="Genotype score"
              value={rsid.score.toFixed(2)}
              tooltip="This is the directional score assigned to your genotype for this rsID before the model combines it with other rsIDs."
            />
          ) : null}
          <StatPill
            label="Weight"
            value={rsid.weight.toFixed(2)}
            tooltip="Weight tells you how much influence this rsID has inside the current simplified trait model."
          />
          {rsid.evidence_level ? (
            <StatPill
              label="Evidence"
              value={formatEvidenceLabel(rsid.evidence_level)}
              tooltip="Evidence level describes how strong the supporting curated research is for this rsID rule."
            />
          ) : null}
        </div>
      </article>
    </Link>
  );
}

export default TraitDetailRsidCard;
