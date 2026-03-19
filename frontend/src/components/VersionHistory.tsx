import { RotateCcw, Upload } from "lucide-react";
import { useVersions, useRestoreVersion } from "../hooks/useVersions";

interface Props {
  assetId: string;
}

export default function VersionHistory({ assetId }: Props) {
  const { data: versions = [], isLoading } = useVersions(assetId);
  const restoreVersion = useRestoreVersion(assetId);

  if (isLoading) return <p className="text-sm text-gray-500">Loading versions...</p>;
  if (versions.length === 0) return <p className="text-sm text-gray-500">No previous versions.</p>;

  return (
    <div className="space-y-2">
      <h3 className="font-medium flex items-center gap-2">
        <Upload className="w-4 h-4" /> Version History
      </h3>
      {versions.map(v => (
        <div key={v.id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded text-sm">
          <div>
            <span className="font-medium">v{v.version_number}</span>
            <span className="text-gray-500 ml-2">{v.file_type} — {Math.round(v.file_size / 1024)}KB</span>
            {v.comment && <span className="text-gray-400 ml-2">"{v.comment}"</span>}
            <span className="text-gray-400 ml-2">{new Date(v.created_at).toLocaleDateString()}</span>
          </div>
          <button
            onClick={() => restoreVersion.mutate(v.id)}
            disabled={restoreVersion.isPending}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" /> Restore
          </button>
        </div>
      ))}
    </div>
  );
}
