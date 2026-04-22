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
      className={`block cursor-pointer rounded-(--radius-card) border px-(--spacing-dropzone-x) py-(--spacing-dropzone-y) text-content shadow-(--shadow-panel) backdrop-blur-sm transition duration-200 ${
        isDragging
          ? 'border-(--color-brand-line) bg-(--color-brand-soft)'
          : 'border-(--color-border-strong) bg-(--color-app-surface)'
      } ${className}`.trim()}
      style={{ backgroundImage: 'var(--background-panel)' }}
    >
      <input
        id={inputId}
        type="file"
        className="sr-only"
        onChange={(event) => handleFiles(event.target.files)}
        accept={accept}
        {...props}
      />

      <div className="flex flex-col items-center gap-3 text-center">
        <div className="inline-flex rounded-full border border-(--color-border) bg-black/20 px-3 py-1 font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
          command interface input
        </div>

        <div className="space-y-2">
          <p className="text-xl font-medium tracking-tight">
            Drag and drop your DNA file here
          </p>
          <p className="text-sm text-content-subtle">
            or click to browse from your computer
          </p>
        </div>

        <p className="font-mono text-xs text-content-faint">
          Supported formats: {supportedFormats.join(', ')}
        </p>
        <p className="rounded-full border border-(--color-border) px-4 py-2 text-sm text-content-muted">
          {selectedFile
            ? `Selected file: ${selectedFile.name}`
            : 'No file selected'}
        </p>
      </div>
    </label>
  );
}

export default FileInput;
