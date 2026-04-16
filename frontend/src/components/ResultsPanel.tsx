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
    return <div className="text-sm">Analyzing file...</div>;
  }

  if (errorMessage) {
    return <div className="text-sm text-red-500">{errorMessage}</div>;
  }

  if (traits.length === 0) {
    return <div className="text-sm">No traits found.</div>;
  }

  return (
    <div className="mx-auto flex w-full max-w-(--width-content) flex-col gap-(--spacing-stack-gap)">
      <div className="p-(--spacing-panel-padding)">
        <p className="text-sm">
          Results for <span>{selectedFile.name}</span>
        </p>
      </div>
      <div className="text-sm">
        Showing {traits.length} traits
        {matchedTraitCount > 0 ? `, ${matchedTraitCount} with matches` : ''}
      </div>
      <div className="grid gap-(--spacing-panel-padding) md:grid-cols-2">
        {traits.map((trait) => (
          <TraitCard key={trait.trait_id} trait={trait} />
        ))}
      </div>
    </div>
  );
}

export default ResultsPanel;
