import { useNavigate } from 'react-router-dom';

import Button from '../components/Button';
import FileInput from '../components/FileInput';
import { useAnalysisSession } from '../context/useAnalysisSession';

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
      <div className="grid w-full items-center gap-grid-gap-lg lg:grid-cols-(--layout-main-columns)">
        <section className="space-y-section-gap">
          <div className="ui-badge">find out exactly who you are</div>

          <div className="space-y-stack-gap">
            <h1 className="max-w-(--width-text) text-display-lg leading-tight sm:text-display-xl">
              Start with a DNA file and explore traits through a clear,
              research-grade interface.
            </h1>
            <p className="max-w-(--width-text) text-base leading-body text-content-subtle">
              Your file will be processed locally and will not be uploaded to
              any server.
            </p>
          </div>

          <div className="ui-panel">
            <p className="ui-eyebrow">get what you need</p>
            <div className="mt-section-offset-lg grid gap-grid-gap-sm sm:grid-cols-2">
              <div className="ui-panel-subtle">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-content-faint">
                  whether...
                </p>
                <p className="mt-section-offset-sm text-sm text-content-muted">
                  You want to understand the underlying algorithms, data
                  processing steps and raw outputs of DNA analysis.
                </p>
              </div>
              <div className="ui-panel-accent">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-content-accent">
                  or
                </p>
                <p className="mt-section-offset-sm text-sm text-content-muted">
                  You're looking for user-friendly, understandable explainations
                  to explore yourself and the world around you.
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

          {selectedFile ? (
            <div className="flex flex-wrap justify-center gap-inline-gap-sm">
              <Button type="submit" disabled={!selectedFile}>
                Continue to analysis
              </Button>
            </div>
          ) : null}
        </form>
      </div>
    </div>
  );
}

export default LandingPage;
