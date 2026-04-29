import type { TraitRsidDetail } from '../types/analysis';
import { formatEvidenceLabel } from '../utils/formatResultLabel';
import StatPill from './StatPill';

type Props = {
  rsid: TraitRsidDetail;
};

const statusClasses: Record<TraitRsidDetail['status'], string> = {
  matched: 'ui-rsid-status-matched',
  no_match: 'ui-rsid-status-no-match',
  missing: 'ui-rsid-status-missing',
};

const statusLabels: Record<TraitRsidDetail['status'], string> = {
  matched: 'Matched rule',
  no_match: 'Observed only',
  missing: 'Missing',
};

const contributionTone: Record<TraitRsidDetail['contribution'], 'default' | 'accent'> = {
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
    <article className={`ui-rsid-card ${statusClasses[rsid.status]}`}>
      <div className="flex flex-wrap items-start justify-between gap-grid-gap-sm">
        <div>
          <div className="flex items-center gap-inline-gap-sm">
            <p className="font-mono text-sm text-content-faint">{rsid.rsid}</p>
            <span className="ui-status-pill">{statusLabels[rsid.status]}</span>
          </div>
          <h3 className="mt-section-offset-sm text-xl text-content">
            {rsid.gene ?? 'Genetic marker'}
          </h3>
        </div>
        <div className="flex flex-wrap gap-inline-gap-sm">
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

      <div className="mt-section-offset-xl grid gap-grid-gap-sm lg:grid-cols-2">
        <div className="ui-panel-subtle">
          <p className="ui-eyebrow">what this marker is</p>
          <p className="mt-section-offset-md text-sm leading-body text-content-muted">
            {rsid.rule_description}
          </p>
          <p className="mt-section-offset-md text-sm leading-body text-content-faint">
            {rsid.status_explanation}
          </p>
        </div>

        <div className="ui-panel-accent">
          <p className="ui-eyebrow text-content-accent">what your genotype means</p>
          <p className="mt-section-offset-md text-sm leading-body text-content-muted">
            {rsid.meaning}
          </p>
          <p className="mt-section-offset-md text-sm leading-body text-content-faint">
            {rsid.contribution_explanation}
          </p>
        </div>
      </div>

      <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
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
  );
}

export default TraitDetailRsidCard;
