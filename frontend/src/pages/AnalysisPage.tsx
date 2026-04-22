import { Link, Navigate } from 'react-router-dom';

import ResultsPanel from '../components/ResultsPanel';
import StatPill from '../components/StatPill';
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
              The overview mirrors the new backend logic: trait-level outcomes
              lead directly into rsID-level explanations, genotype meaning, and
              progressive disclosure.
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
