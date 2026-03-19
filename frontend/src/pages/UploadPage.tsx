import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, CheckCircle2, AlertCircle } from "lucide-react";
import { useUploadAsset } from "../hooks/useAssets";
import { Button } from "../components/ui/Button";

export default function UploadPage() {
  const navigate = useNavigate();
  const upload = useUploadAsset();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      setSelectedFile(file);
      upload.mutate(file, {
        onSuccess: (asset) => {
          setTimeout(() => navigate(`/assets/${asset.id}`), 1200);
        },
      });
    },
    [upload, navigate]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [], "video/*": [] },
    maxSize: 50 * 1024 * 1024,
    multiple: false,
    disabled: upload.isPending || upload.isSuccess,
  });

  return (
    <div>
      <h1 className="text-display text-text-primary">Upload Asset</h1>
      <p className="mt-2 text-body text-text-secondary">
        Drag and drop your image or video file. AI will generate captions and
        hashtags automatically.
      </p>

      <div
        {...getRootProps()}
        className={`mt-xl flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all duration-200 ${
          isDragActive
            ? "border-accent bg-accent-subtle"
            : "border-border hover:border-accent/40 hover:bg-accent-subtle/50"
        }`}
        style={{ minHeight: "60vh" }}
      >
        <input {...getInputProps()} />

        <AnimatePresence mode="wait">
          {upload.isSuccess ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center gap-4"
            >
              <motion.div
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.4 }}
              >
                <CheckCircle2 className="h-16 w-16 text-success" strokeWidth={1.2} />
              </motion.div>
              <p className="text-heading text-text-primary">Upload complete</p>
              <p className="text-body text-text-secondary">
                Redirecting to asset detail...
              </p>
            </motion.div>
          ) : upload.isPending ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-4"
            >
              <div className="h-12 w-12 animate-spin rounded-full border-[3px] border-accent border-t-transparent" />
              <p className="text-body-medium text-text-primary">
                Uploading {selectedFile?.name}...
              </p>
              <p className="text-caption text-text-tertiary">
                {selectedFile && `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`}
              </p>
            </motion.div>
          ) : upload.isError ? (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-4"
            >
              <AlertCircle className="h-12 w-12 text-danger" strokeWidth={1.2} />
              <p className="text-body-medium text-danger">Upload failed</p>
              <Button variant="secondary" onClick={() => upload.reset()}>
                Try again
              </Button>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center gap-4"
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-subtle">
                <Upload
                  className="h-8 w-8 text-accent"
                  strokeWidth={1.2}
                />
              </div>
              <div className="text-center">
                <p className="text-body-medium text-text-primary">
                  {isDragActive
                    ? "Drop your file here"
                    : "Drag and drop your file here"}
                </p>
                <p className="mt-1 text-caption text-text-tertiary">
                  or click to browse &middot; Images and videos up to 50 MB
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
