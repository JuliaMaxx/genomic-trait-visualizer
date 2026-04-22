import { Link } from 'react-router-dom';
import type { TraitResult } from '../types/analysis';
import { formatConfidence } from '../utils/formatConfidence';
import { formatCategoryLabel } from '../utils/formatResultLabel';
import ResultToneBadge from './ResultToneBadge';
import StatPill from './StatPill';

type Props = {
  trait: TraitResult;
};

function TraitCard({ trait }: Props) {
  return (
    <Link
      to={`/analysis/traits/${trait.trait_id}`}
      className="flex flex-col justify-between ui-panel-gradient group transition duration-200 hover:-translate-y-0.5 hover:border-brand-line hover:shadow-button"
    >
      <div className="flex items-start justify-between gap-inline-gap">
        <div>
          <p className="ui-eyebrow">{formatCategoryLabel(trait.category)}</p>
          <h3 className="mt-section-offset-sm text-xl text-content transition group-hover:text-content-accent">
            {trait.name}
          </h3>
          <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
            {trait.simple_summary}
          </p>
        </div>
        <ResultToneBadge result={trait.result} />
      </div>

      <div>
        <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
          <StatPill
            label="Confidence"
            value={formatConfidence(trait.confidence)}
          />
          <StatPill
            label="Matched rsIDs"
            value={String(trait.matched_rsids.length)}
            tone="accent"
          />
          <StatPill
            label="Missing rsIDs"
            value={String(trait.missing_rsids.length)}
          />
        </div>

        <div className="mt-section-offset-xl flex items-center justify-between text-sm text-content-faint">
          <span className="font-mono">{trait.trait_id}</span>
          <span>Open drill-down</span>
        </div>
      </div>
    </Link>
  );
}

export default TraitCard;
