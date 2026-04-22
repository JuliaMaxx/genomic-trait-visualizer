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
    <article className="ui-panel-gradient">
      <div className="flex items-start justify-between gap-inline-gap">
        <div>
          <p className="ui-eyebrow">
            trait interpretation
          </p>
          <h3 className="mt-section-offset-sm text-xl text-content">
            {trait.name}
          </h3>
          <p className="mt-1 font-mono text-xs text-content-faint">
            {trait.trait_id}
          </p>
        </div>
        <span className="ui-status-pill">
          Confidence {formatConfidence(trait.confidence)}
        </span>
      </div>

      <div className="mt-section-offset-xl space-y-stack-gap text-sm">
        <div>
          <p className="ui-eyebrow">
            matched rules
          </p>
          {trait.matched_rules.length === 0 ? (
            <p className="mt-section-offset-sm text-content-subtle">
              No matching rules for this upload.
            </p>
          ) : (
            <ul className="mt-section-offset-sm space-y-section-offset-sm">
              {trait.matched_rules.map((rule, index) => (
                <li key={`${trait.trait_id}-${rule.rsid}-${index}`}>
                  <div className="ui-panel-accent text-sm">
                    <p className="font-mono text-sm font-medium text-content-accent">
                      {rule.rsid} -{' '}
                      {Array.isArray(rule.genotype)
                        ? rule.genotype.join(', ')
                        : rule.genotype}
                    </p>
                    <p className="mt-section-offset-sm text-content-muted">
                      {rule.description}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="ui-eyebrow">
            missing rsids
          </p>
          <p className="mt-section-offset-sm text-content-subtle">
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
