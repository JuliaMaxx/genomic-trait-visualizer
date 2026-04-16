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
    <div className="flex flex-1 items-center justify-center py-(--spacing-card-padding)">
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
