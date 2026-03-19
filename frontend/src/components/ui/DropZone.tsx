import { useCallback } from "react";
import { useDropzone, type DropzoneOptions } from "react-dropzone";
import { Upload } from "lucide-react";
import { cn } from "../../lib/cn";

interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  accept?: DropzoneOptions["accept"];
  maxSize?: number;
  multiple?: boolean;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function DropZone({
  onFilesAccepted,
  accept = { "image/*": [], "video/*": [] },
  maxSize = 50 * 1024 * 1024,
  multiple = false,
  disabled = false,
  className,
  children,
}: DropZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFilesAccepted(accepted);
    },
    [onFilesAccepted]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize,
    multiple,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all duration-200",
        isDragActive
          ? "border-accent bg-accent-subtle"
          : "border-border hover:border-accent/40 hover:bg-accent-subtle/50",
        disabled && "pointer-events-none opacity-50",
        className
      )}
    >
      <input {...getInputProps()} />
      {children || (
        <div className="flex flex-col items-center gap-4 p-xl">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-subtle">
            <Upload className="h-7 w-7 text-accent" strokeWidth={1.2} />
          </div>
          <div className="text-center">
            <p className="text-body-medium text-text-primary">
              {isDragActive ? "Drop your file here" : "Drag and drop your file here"}
            </p>
            <p className="mt-1 text-caption text-text-tertiary">
              or click to browse &middot; Up to {Math.round(maxSize / (1024 * 1024))} MB
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
