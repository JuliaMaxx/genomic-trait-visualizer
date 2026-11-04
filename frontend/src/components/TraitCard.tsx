import { Link } from 'react-router-dom';
import type { TraitAnalysisSummary } from '../types/api';
import { formatConfidence } from '../utils/formatConfidence';
import ResultToneBadge from './ResultToneBadge';
import StatPill from './StatPill';

type Props = {
  trait: TraitAnalysisSummary;
};

function TraitCard({ trait }: Props) {
  const matchedCount = trait.rule_statuses.filter(
    (rule) => rule.status === 'matched',
  ).length;
  const missingCount = trait.rule_statuses.filter(
    (rule) => rule.status === 'missing',
  ).length;

  return (
    <Link
      to={`/analysis/traits/${trait.trait_id}`}
      className="group ui-card-link"
    >
      <div className="flex items-start justify-between gap-md">
        <div>
          <p className="ui-eyebrow">{trait.category}</p>
          <h3 className="ui-card-link-heading">{trait.name}</h3>
          <p className="leading-regular ui-paragraph-subtle">
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
            value={String(matchedCount)}
            tone="accent"
            tooltip="Matched rules means how many curated genotype rules for this trait were matched by your uploaded DNA data."
          />
          <StatPill
            label="Missing rules"
            value={String(missingCount)}
            tooltip="Missing rules means rsIDs used by this trait model that were not available in your uploaded DNA file."
          />
        </div>
      </div>
    </Link>
  );
}

export default TraitCard;
