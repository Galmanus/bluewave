import { Download, X } from "lucide-react";
import { useState } from "react";
import api from "../lib/api";

interface Props {
  selectedIds: string[];
  onClear: () => void;
}

export default function SelectionToolbar({ selectedIds, onClear }: Props) {
  const [exporting, setExporting] = useState(false);

  if (selectedIds.length === 0) return null;

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await api.post("/api/v1/assets/export", { asset_ids: selectedIds }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "bluewave_export.zip";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-900 text-white rounded-xl px-5 py-3 shadow-2xl flex items-center gap-4 z-50 animate-in slide-in-from-bottom">
      <span className="text-sm font-medium">{selectedIds.length} selected</span>
      <div className="w-px h-5 bg-gray-600" />
      <button
        onClick={handleExport}
        disabled={exporting}
        className="flex items-center gap-1.5 text-sm hover:text-blue-400 transition"
      >
        <Download className="w-4 h-4" />
        {exporting ? "Exporting..." : "Export ZIP"}
      </button>
      <button onClick={onClear} className="flex items-center gap-1 text-sm hover:text-gray-400 transition">
        <X className="w-4 h-4" /> Clear
      </button>
    </div>
  );
}
