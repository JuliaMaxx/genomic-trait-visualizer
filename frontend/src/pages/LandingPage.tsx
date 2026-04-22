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
    <div className="flex flex-1 items-center justify-center py-8">
      <div className="grid w-full items-start gap-6 lg:grid-cols-(--layout-main-columns)">
        <section className="space-y-6">
          <div className="inline-flex rounded-full border border-border bg-white/3 px-3 py-1.5 font-mono text-eyebrow uppercase tracking-eyebrow text-content-faint">
            command-driven genomic upload
          </div>

          <div className="space-y-4">
            <h1 className="max-w-(--width-text) text-display-lg leading-tight sm:text-display-xl">
              Start with a DNA file and explore traits through a clearer,
              research-grade interface.
            </h1>
            <p className="max-w-(--width-text) text-base leading-7 text-content-subtle">
              Your file will be processed locally and will not be uploaded to
              any server.
            </p>
          </div>

          <div className="rounded-(--radius-card) border border-border-strong bg-app-surface p-(--spacing-card-padding) shadow-(--shadow-panel) backdrop-blur-sm">
            <p className="font-mono text-eyebrow uppercase tracking-eyebrow text-content-faint">
              dual-layer interface note
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-panel border border-border bg-black/15 p-4">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-content-faint">
                  data layer
                </p>
                <p className="mt-2 text-sm text-content-muted">
                  Upload inputs stay visually distinct from analysis results so
                  the workflow feels more transparent.
                </p>
              </div>
              <div className="rounded-panel border border-brand-line bg-brand-soft p-4">
                <p className="font-mono text-xs uppercase tracking-eyebrow text-orange-200">
                  interpretation layer
                </p>
                <p className="mt-2 text-sm text-content-muted">
                  Warm accent surfaces highlight meaning and outcome without
                  changing the scope of the current feature set.
                </p>
              </div>
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="flex w-full flex-col gap-4">
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
