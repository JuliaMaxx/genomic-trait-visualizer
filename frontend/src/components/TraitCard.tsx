import { formatConfidence } from '../utils/formatConfidence';

type Props = {
  trait: Trait;
};

// TODO: make confidence more visually prominent, e.g. with colors or icons
// TODO: change when backened simplifies this
// TODO: make sure long lists look good too, eg. +X more
// TODO: add odds ration and notes that are returned from the backend
function TraitCard({ trait }: Props) {
  return (
    <article className="rounded-(--radius-base) border-(--border-base) p-(--spacing-card-padding)">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg">{trait.name}</h3>
          <p className="mt-1 text-sm">{trait.trait_id}</p>
        </div>
        <span
          className={`rounded-(--radius-base) border-(--border-base) px-2 py-1 text-xs`}
        >
          Confidence {formatConfidence(trait.confidence)}
        </span>
      </div>

      <div className="mt-5 space-y-4 text-sm">
        <div>
          <p className="font-medium">Matched rules</p>
          {trait.matched_rules.length === 0 ? (
            <p className="mt-1">No matching rules for this upload.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {trait.matched_rules.map((rule) => (
                <li key={`${trait.trait_id}`}>
                  <div
                    className={`rounded-(--radius-base) border-(--border-base) p-(--spacing-panel-padding) text-sm`}
                  >
                    <p className="font-medium">
                      {rule.rsid} -{' '}
                      {Array.isArray(rule.genotype)
                        ? rule.genotype.join(', ')
                        : rule.genotype}
                    </p>
                    <p className="mt-1">{rule.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="font-medium">Missing RSIDs</p>
          <p className="mt-1">
            {trait.missing_rsids.length > 0
              ? trait.missing_rsids.join(', ')
              : 'None'}
          </p>
        </div>
      </div>
    </article>
  );
}

export default TraitCard;
