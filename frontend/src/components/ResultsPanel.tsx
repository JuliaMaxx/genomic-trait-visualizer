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
      <div className="w-full max-w-(--width-content) rounded-(--radius-card) border border-(--color-border-strong) bg-(--color-app-surface) p-(--spacing-card-padding) text-sm text-content-muted shadow-(--shadow-panel) backdrop-blur-sm">
        <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
          analysis status
        </p>
        <p className="mt-3 text-base text-content">Analyzing file...</p>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="w-full max-w-(--width-content) rounded-(--radius-card) border border-rose-500/30 bg-rose-500/8 p-(--spacing-card-padding) text-sm text-rose-200 shadow-(--shadow-panel)">
        {errorMessage}
      </div>
    );
  }

  if (traits.length === 0) {
    return (
      <div className="w-full max-w-(--width-content) rounded-(--radius-card) border border-(--color-border-strong) bg-(--color-app-surface) p-(--spacing-card-padding) text-sm text-content-muted shadow-(--shadow-panel) backdrop-blur-sm">
        No traits found.
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-(--width-content) flex-col gap-(--spacing-stack-gap)">
      <div className="rounded-(--radius-card) border border-(--color-border-strong) bg-(--color-app-surface) p-(--spacing-card-padding) shadow-(--shadow-panel) backdrop-blur-sm">
        <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
          interpretation summary
        </p>
        <p className="mt-3 text-lg font-medium tracking-tight text-content">
          Results for <span className="text-brand">{selectedFile.name}</span>
        </p>
        <p className="mt-2 text-sm text-content-subtle">
          Showing {traits.length} traits
          {matchedTraitCount > 0 ? `, ${matchedTraitCount} with matches` : ''}
        </p>
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
