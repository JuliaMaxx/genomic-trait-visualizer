import { Navigate } from 'react-router-dom';

import ResultsPanel from '../components/ResultsPanel';
import { useAnalysisSession } from '../context/useAnalysisSession';
import useTraitAnalysis from '../hooks/useTraitAnalysis';

// TODO: error first UI if (errorMessage) return ErrorComponent
function AnalysisPage() {
  const { selectedFile } = useAnalysisSession();
  const { traits, errorMessage, isLoading } = useTraitAnalysis(selectedFile);

  if (!selectedFile) {
    return <Navigate to="/" replace />;
  }

  const matchedTraitCount = traits.filter(
    (trait) => trait.matched_rules.length > 0,
  ).length;

  return (
    <div className="flex flex-1 flex-col gap-6 py-(--spacing-card-padding)">
      <section className="max-w-(--width-content)">
        <div className="inline-flex rounded-full border border-(--color-border) bg-white/3 px-3 py-1.5 font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
          progressive disclosure results
        </div>
        <h1 className="mt-4 text-3xl sm:text-4xl">Trait analysis overview</h1>
        <p className="mt-3 max-w-(--width-text) text-base leading-7 text-content-subtle">
          The analysis flow is unchanged. This view simply presents upload
          inputs and interpreted trait signals with clearer hierarchy and a more
          consistent scientific UI.
        </p>
      </section>

      <ResultsPanel
        errorMessage={errorMessage}
        isLoading={isLoading}
        matchedTraitCount={matchedTraitCount}
        selectedFile={selectedFile}
        traits={traits}
      />
    </div>
  );
}

export default AnalysisPage;
