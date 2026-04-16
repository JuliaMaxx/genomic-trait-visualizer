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
    <div className="flex flex-1 flex-col items-center text-center justify-center gap-(--spacing-section-gap)">
      <h1 className="text-3xl sm:text-4xl">Start with a DNA file</h1>
      <p className="max-w-(--width-text) text-base">
        Your file will be processed locally and will not be uploaded to any
        server.
      </p>

      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-(--width-form) flex-col gap-(--spacing-panel-padding)"
      >
        <FileInput
          onFileSelect={setSelectedFile}
          selectedFile={selectedFile}
          accept=".tsv,.csv,.vcf,.txt"
        />

        <Button type="submit" disabled={!selectedFile} className="self-center">
          Continue to analysis
        </Button>
      </form>
    </div>
  );
}

export default LandingPage;
