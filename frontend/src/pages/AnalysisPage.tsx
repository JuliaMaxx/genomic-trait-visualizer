import { Link, Navigate } from 'react-router-dom';

import ResultsPanel from '../components/ResultsPanel';
import { useAnalysisSession } from '../context/useAnalysisSession';
import useTraitOverview from '../hooks/useTraitOverview';

function AnalysisPage() {
  const { selectedFile } = useAnalysisSession();
  const { traits, errorMessage, isLoading } = useTraitOverview(selectedFile);

  if (!selectedFile) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex flex-1 flex-col gap-grid-gap py-card-padding">
      <section className="flex flex-col gap-grid-gap">
        <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
          <div>
            <h1 className="mt-section-offset-lg text-3xl sm:text-4xl">
              Trait exploration overview
            </h1>
            <p className="mt-section-offset-md max-w-(--width-text) text-base leading-body text-content-subtle">
              This page shows the traits that could be checked using your
              uploaded DNA file. Start with the short summaries here, then open
              any trait to see the rsIDs behind the result and how your
              genotypes were interpreted.
            </p>
          </div>

          <Link to="/" className="ui-button-base ui-button-secondary">
            Change file
          </Link>
        </div>
      </section>

      <ResultsPanel
        errorMessage={errorMessage}
        isLoading={isLoading}
        selectedFile={selectedFile}
        traits={traits}
      />
    </div>
  );
}

export default AnalysisPage;
