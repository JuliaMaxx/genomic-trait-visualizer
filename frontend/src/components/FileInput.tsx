import { type DragEvent, useId, useState } from 'react';

type Props = {
  onFileSelect?: (file: File | null) => void;
  selectedFile: File | null;
  supportedFormats?: string[];
  className?: string;
  accept?: string;
};

const defaultFormats = ['.tsv', '.csv', '.vcf', '.txt'];

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

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
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
      className={`${isDragging ? 'ui-dropzone ui-dropzone-active' : 'ui-dropzone bg-panel-gradient'} ${className}`.trim()}
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
          Your journey starts here
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
