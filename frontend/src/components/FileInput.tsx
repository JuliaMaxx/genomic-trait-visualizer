import { type DragEvent, useId, useState } from 'react';

type Props = {
  onFileSelect?: (file: File | null) => void;
  selectedFile: File | null;
  supportedFormats?: string;
  className?: string;
};

const defaultFormats = '.tsv, .csv, .vcf, .txt';

function FileInput({
  className = '',
  onFileSelect,
  selectedFile,
  supportedFormats = defaultFormats,
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
        accept={supportedFormats}
        {...props}
      />

      <div className="flex flex-col items-center gap-inline-gap-sm text-center">
        <div className="ui-badge-strong">Your journey starts here</div>

        <div className="space-y-section-offset-sm">
          <p className="ui-paragraph-strong">
            Drag and drop your DNA file here
          </p>
          <p className="ui-paragraph-subtle">
            or click to browse from your computer
          </p>
        </div>

        <p className="ui-paragraph-faint">
          Supported formats: {supportedFormats}
        </p>

        <p className="ui-pill">
          {selectedFile
            ? `Selected file: ${selectedFile.name}`
            : 'Uppload a file to continue'}
        </p>
      </div>
    </label>
  );
}

export default FileInput;
