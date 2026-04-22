import { useId, useState } from 'react';

type Props = {
  onFileSelect?: (file: File | null) => void;
  selectedFile: File | null;
  supportedFormats?: string[];
  className?: string;
  accept?: string;
};

const defaultFormats = ['.tsv', '.csv', '.vcf', '.txt'];

// TODO: validate file's size and type
// TODO: add error handling: invalid format, empty file, corrupted file
// TODO: add keyboard accessibility
// TODO: handle drag flicker issues
function FileInput({
  className = '',
  onFileSelect,
  selectedFile,
  supportedFormats = defaultFormats,
  accept,
  ...props
}: Props) {
  const inputId = useId();
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(fileList: FileList | null) {
    const file = fileList?.[0] ?? null;
    onFileSelect?.(file);
  }

  function handleDragOver(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <label
      htmlFor={inputId}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`bg-panel-gradient block cursor-pointer rounded-card border px-dropzone-x py-dropzone-y text-content shadow-panel backdrop-blur-sm transition duration-200 ${
        isDragging
          ? 'border-brand-line bg-brand-soft'
          : 'border-border-strong bg-app-surface'
      } ${className}`.trim()}
    >
      <input
        id={inputId}
        type="file"
        className="sr-only"
        onChange={(event) => handleFiles(event.target.files)}
        accept={accept}
        {...props}
      />

      <div className="flex flex-col items-center gap-inline-gap-sm text-center">
        <div className="ui-badge bg-surface-overlay-strong py-1">
          command interface input
        </div>

        <div className="space-y-section-offset-sm">
          <p className="text-xl font-medium leading-tight tracking-tight">
            Drag and drop your DNA file here
          </p>
          <p className="text-sm text-content-subtle">
            or click to browse from your computer
          </p>
        </div>

        <p className="ui-eyebrow text-xs normal-case tracking-normal">
          Supported formats: {supportedFormats.join(', ')}
        </p>
        <p className="rounded-pill border border-border px-pill-x py-pill-y text-sm text-content-muted">
          {selectedFile
            ? `Selected file: ${selectedFile.name}`
            : 'No file selected'}
        </p>
      </div>
    </label>
  );
}

export default FileInput;
