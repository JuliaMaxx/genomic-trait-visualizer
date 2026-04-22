import type { TraitRsidDetail } from '../types/analysis';
import StatPill from './StatPill';

type Props = {
  rsid: TraitRsidDetail;
};

const statusClasses: Record<TraitRsidDetail['status'], string> = {
  matched: 'border-emerald-400/25 bg-emerald-400/8',
  no_match: 'border-amber-300/20 bg-surface-overlay',
  missing: 'border-border bg-surface-overlay-muted',
};

const statusLabels: Record<TraitRsidDetail['status'], string> = {
  matched: 'Matched',
  no_match: 'Observed',
  missing: 'Missing',
};

function formatGenotype(genotype: string[] | null) {
  if (!genotype || genotype.length === 0) {
    return 'Not available';
  }

  return genotype.join('');
}

function TraitDetailRsidCard({ rsid }: Props) {
  return (
    <article
      className={`rounded-card border p-card-padding shadow-panel backdrop-blur-sm ${statusClasses[rsid.status]}`}
    >
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
          />
          {rsid.genotype ? (
            <StatPill
              label="Known genotypes"
              value={rsid.genotype.join(', ')}
            />
          ) : null}
        </div>
      </div>

      <div className="mt-section-offset-xl grid gap-grid-gap-sm lg:grid-cols-2">
        <div className="ui-panel-subtle">
          <p className="ui-eyebrow">genetic basis</p>
          <p className="mt-section-offset-md text-sm leading-body text-content-muted">
            {rsid.rule_description}
          </p>
        </div>

        <div className="ui-panel-accent">
          <p className="ui-eyebrow text-content-accent">
            meaning for this genotype
          </p>
          <p className="mt-section-offset-md text-sm leading-body text-content-muted">
            {rsid.meaning}
          </p>
        </div>
      </div>

      <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
        {rsid.effect ? (
          <StatPill label="Effect" value={rsid.effect} tone="accent" />
        ) : null}
        {rsid.odds_ratio ? (
          <StatPill label="Odds ratio" value={rsid.odds_ratio.toFixed(2)} />
        ) : null}
        {typeof rsid.score === 'number' ? (
          <StatPill label="Score" value={rsid.score.toFixed(2)} />
        ) : null}
      </div>
    </article>
  );
}

export default TraitDetailRsidCard;
