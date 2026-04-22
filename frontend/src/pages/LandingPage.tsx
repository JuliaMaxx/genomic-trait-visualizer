import { useNavigate } from 'react-router-dom';

import { useAnalysisSession } from '../context/useAnalysisSession';
import Button from '../components/Button';
import FileInput from '../components/FileInput';

function LandingPage() {
  const navigate = useNavigate();
  const { selectedFile, setSelectedFile } = useAnalysisSession();

  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedFile) {
      return;
    }

    navigate('/analysis');
  };

  return (
    <div className="flex flex-1 items-center justify-center py-page-y">
      <div className="grid w-full items-start gap-grid-gap lg:grid-cols-(--layout-main-columns)">
        <section className="space-y-section-gap">
          <div className="ui-badge">command-driven genomic upload</div>

          <div className="space-y-stack-gap">
            <h1 className="max-w-(--width-text) text-display-lg leading-tight sm:text-display-xl">
              Start with a DNA file and explore traits through a clearer,
              research-grade interface.
            </h1>
            <p className="max-w-(--width-text) text-base leading-body text-content-subtle">
              Your file will be processed locally and will not be uploaded to
              any server.
            </p>
          </div>

          <div className="ui-panel">
            <p className="ui-eyebrow">dual-layer interface note</p>
            <div className="mt-section-offset-lg grid gap-grid-gap-sm sm:grid-cols-2">
              <div className="ui-panel-subtle">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-content-faint">
                  data layer
                </p>
                <p className="mt-section-offset-sm text-sm text-content-muted">
                  Upload inputs stay visually distinct from analysis results so
                  the workflow feels more transparent.
                </p>
              </div>
              <div className="ui-panel-accent">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-content-accent">
                  interpretation layer
                </p>
                <p className="mt-section-offset-sm text-sm text-content-muted">
                  Warm accent surfaces highlight meaning and outcome without
                  changing the scope of the current feature set.
                </p>
              </div>
            </div>
          </div>
        </section>

        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-grid-gap-sm"
        >
          <FileInput
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
            accept=".tsv,.csv,.vcf,.txt"
          />

          <Button type="submit" disabled={!selectedFile} className="self-start">
            Continue to analysis
          </Button>
        </form>
      </div>
    </div>
  );
}

export default LandingPage;
