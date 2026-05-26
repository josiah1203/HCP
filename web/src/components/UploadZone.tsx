import { useCallback, useState, type DragEvent } from "react";

interface UploadZoneProps {
  onFiles: (files: FileList) => void;
  disabled?: boolean;
  label?: string;
}

export function UploadZone({
  onFiles,
  disabled = false,
  label = "Drop hardware files here or click to browse",
}: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled || !e.dataTransfer.files.length) return;
      onFiles(e.dataTransfer.files);
    },
    [disabled, onFiles]
  );

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload files"
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragOver ? "border-hcp-500 bg-hcp-50" : "border-slate-300 bg-white"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:border-hcp-500"}`}
    >
      <p className="text-slate-600 mb-3">{label}</p>
      <label className="inline-block">
        <span className="sr-only">Choose files</span>
        <input
          type="file"
          multiple
          disabled={disabled}
          className="text-sm"
          onChange={(e) => {
            if (e.target.files?.length) onFiles(e.target.files);
          }}
        />
      </label>
    </div>
  );
}
