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
    <div className="flex flex-1 flex-col gap-grid-gap py-card-padding">
      <section className="max-w-(--width-content)">
        <div className="ui-badge">progressive disclosure results</div>
        <h1 className="mt-section-offset-lg text-3xl sm:text-4xl">
          Trait analysis overview
        </h1>
        <p className="mt-section-offset-md max-w-(--width-text) text-base leading-body text-content-subtle">
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
