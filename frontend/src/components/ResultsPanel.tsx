import TraitCard from './TraitCard';

type Props = {
  errorMessage: string;
  isLoading: boolean;
  matchedTraitCount: number;
  selectedFile: File;
  traits: Trait[];
};

function ResultsPanel({
  errorMessage,
  isLoading,
  matchedTraitCount,
  selectedFile,
  traits,
}: Props) {
  if (isLoading) {
    return (
      <div className="ui-panel w-full max-w-(--width-content) text-sm text-content-muted">
        <p className="ui-eyebrow">analysis status</p>
        <p className="mt-section-offset-md text-base text-content">
          Analyzing file...
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
        No traits found.
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-(--width-content) flex-col gap-stack-gap">
      <div className="ui-panel">
        <p className="ui-eyebrow">interpretation summary</p>
        <p className="mt-section-offset-md text-lg font-medium leading-tight tracking-tight text-content">
          Results for <span className="text-brand">{selectedFile.name}</span>
        </p>
        <p className="mt-section-offset-sm text-sm text-content-subtle">
          Showing {traits.length} traits
          {matchedTraitCount > 0 ? `, ${matchedTraitCount} with matches` : ''}
        </p>
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
