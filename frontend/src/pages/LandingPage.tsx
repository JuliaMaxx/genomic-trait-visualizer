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
    <div className="flex flex-1 items-center justify-center py-3xl">
      <div className="grid items-center gap-3xl lg:grid-cols-2">
        <section className="space-y-xl">
          <div className="ui-badge">find out exactly who you are</div>

          <div className="flex flex-col gap-md">
            <h1 className="ui-detail-title">
              Start with a DNA file and explore traits through a clear,
              research-grade interface.
            </h1>
            <p className="ui-detail-lede">
              Your file will be processed locally and will not be uploaded to
              any server.
            </p>
          </div>

          <div className="ui-panel">
            <p className="ui-eyebrow">get what you need</p>
            <div className="mt-md grid gap-md sm:grid-cols-2">
              <div className="ui-panel-subtle">
                <p className="ui-eyebrow text-xs">whether...</p>
                <p className="ui-paragraph-muted mt-2xs">
                  You want to understand the underlying algorithms, data
                  processing steps and raw outputs of DNA analysis.
                </p>
              </div>
              <div className="ui-panel-accent">
                <p className="ui-eyebrow-accent text-xs">or</p>
                <p className="ui-paragraph-muted mt-2xs">
                  You're looking for user-friendly, understandable explainations
                  to explore yourself and the world around you.
                </p>
              </div>
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="flex flex-col gap-md">
          <FileInput
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
          />

          {selectedFile ? (
            <div className="flex justify-center">
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
