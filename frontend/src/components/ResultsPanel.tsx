import type { TraitResult } from '../types/analysis';
import StatPill from './StatPill';
import TraitCard from './TraitCard';

type Props = {
  errorMessage: string;
  isLoading: boolean;
  selectedFile: File;
  traits: TraitResult[];
};

function ResultsPanel({
  errorMessage,
  isLoading,
  selectedFile,
  traits,
}: Props) {
  if (isLoading) {
    return (
      <div className="ui-panel w-full max-w-(--width-content)">
        <p className="ui-eyebrow">analysis status</p>
        <p className="mt-section-offset-md text-base text-content">
          Reading your uploaded DNA and evaluating mapped traits.
        </p>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error w-full max-w-(--width-content)">
        {errorMessage}
      </div>
    );
  }

  if (traits.length === 0) {
    return (
      <div className="ui-panel w-full max-w-(--width-content) text-sm text-content-muted">
        No traits were returned for this upload.
      </div>
    );
  }

  const matchedTraitCount = traits.filter(
    (trait) => trait.matched_rsids.length > 0,
  ).length;
  const likelyCount = traits.filter(
    (trait) => trait.result === 'likely',
  ).length;

  return (
    <div className="mx-auto flex w-full max-w-(--width-content) flex-col gap-stack-gap">
      <div className="ui-panel">
        <p className="ui-eyebrow">analysis summary</p>
        <p className="mt-section-offset-md text-lg font-medium leading-tight tracking-tight text-content">
          Results for <span className="text-brand">{selectedFile.name}</span>
        </p>
        <p className="mt-section-offset-sm max-w-(--width-text) text-sm leading-body text-content-subtle">
          Each card is an exploration entry point. Open any trait to trace its
          result back to the rsIDs, genotypes, and interpretation logic returned
          by the backend.
        </p>

        <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
          <StatPill label="Traits" value={String(traits.length)} />
          <StatPill
            label="With matches"
            value={String(matchedTraitCount)}
            tone="accent"
          />
          <StatPill label="Likely results" value={String(likelyCount)} />
        </div>
      </div>

      <div className="grid gap-panel-padding md:grid-cols-2">
        {traits.map((trait) => (
          <TraitCard key={trait.trait_id} trait={trait} />
        ))}
      </div>
    </div>
  );
}

export default ResultsPanel;
