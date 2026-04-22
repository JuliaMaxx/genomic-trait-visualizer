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
    <article
      className="rounded-(--radius-card) border border-(--color-border-strong) p-(--spacing-card-padding) shadow-(--shadow-panel) backdrop-blur-sm"
      style={{ backgroundImage: 'var(--background-panel)' }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
            trait interpretation
          </p>
          <h3 className="mt-2 text-xl text-content">{trait.name}</h3>
          <p className="mt-1 font-mono text-xs text-content-faint">
            {trait.trait_id}
          </p>
        </div>
        <span
          className="rounded-full border border-(--color-border) bg-black/20 px-3 py-1.5 text-xs text-content-muted"
        >
          Confidence {formatConfidence(trait.confidence)}
        </span>
      </div>

      <div className="mt-5 space-y-4 text-sm">
        <div>
          <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
            matched rules
          </p>
          {trait.matched_rules.length === 0 ? (
            <p className="mt-2 text-content-subtle">
              No matching rules for this upload.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {trait.matched_rules.map((rule, index) => (
                <li key={`${trait.trait_id}-${rule.rsid}-${index}`}>
                  <div
                    className="rounded-(--radius-panel) border border-(--color-brand-line) bg-(--color-brand-soft) p-(--spacing-panel-padding) text-sm"
                  >
                    <p className="font-mono text-sm font-medium text-orange-100">
                      {rule.rsid} -{' '}
                      {Array.isArray(rule.genotype)
                        ? rule.genotype.join(', ')
                        : rule.genotype}
                    </p>
                    <p className="mt-2 text-content-muted">{rule.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
            missing rsids
          </p>
          <p className="mt-2 text-content-subtle">
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
