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
      className={`block cursor-pointer rounded-(--radius-base) border border-dashed px-(--spacing-dropzone-x) py-(--spacing-dropzone-y) ${
        isDragging ? 'border-brand' : 'border-content'
      } text-content ${className}`.trim()}
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
        <div>
          <p className="text-base">Drag and drop your DNA file here</p>
          <p className="mt-1 text-sm">or click to browse from your computer</p>
        </div>

        <p className="text-sm">
          Supported formats: {supportedFormats.join(', ')}
        </p>
        <p className="text-sm">
          {selectedFile
            ? `Selected file: ${selectedFile.name}`
            : 'No file selected'}
        </p>
      </div>
    </label>
  );
}

export default FileInput;
