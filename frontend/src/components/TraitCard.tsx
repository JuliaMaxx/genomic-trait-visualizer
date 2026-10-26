import { Link } from 'react-router-dom';
import type { TraitResult } from '../types/analysis';
import { formatConfidence } from '../utils/formatConfidence';
import ResultToneBadge from './ResultToneBadge';
import StatPill from './StatPill';

type Props = {
  trait: TraitResult;
};

function TraitCard({ trait }: Props) {
  return (
    <Link
      to={`/analysis/traits/${trait.trait_id}`}
      className="group ui-card-link"
    >
      <div className="flex items-start justify-between gap-inline-gap">
        <div>
          <p className="ui-eyebrow">{trait.category}</p>
          <h3 className="ui-card-link-heading">{trait.name}</h3>
          <p className="leading-body ui-paragraph-subtle">
            {trait.description}
          </p>
        </div>
        <ResultToneBadge
          result={trait.result}
          tooltip={trait.result_badge_tooltip}
        />
      </div>

      <div>
        <div className="ui-pill-collection">
          <StatPill
            label="Confidence"
            value={formatConfidence(trait.confidence)}
            tooltip="Confidence tells you how dependable this educational result is. It is influenced by data completeness and evidence strength, not certainty."
          />
          <StatPill
            label="Matched rules"
            value={String(trait.matched_rsids.length)}
            tone="accent"
            tooltip="Matched rules means how many curated genotype rules for this trait were matched by your uploaded DNA data."
          />
          <StatPill
            label="Missing rules"
            value={String(trait.missing_rsids.length)}
            tooltip="Missing rules means rsIDs used by this trait model that were not available in your uploaded DNA file."
          />
        </div>
      </div>
    </Link>
  );
}

export default TraitCard;
