import { DollarSign } from "lucide-react";

interface ROIData {
  estimated_hours_saved: number;
  estimated_cost_saved_usd: number;
  assets_processed: number;
}

export default function ROICard({ data }: { data: ROIData }) {
  return (
    <div className="bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-xl p-6">
      <div className="flex items-center gap-2 mb-3">
        <DollarSign className="w-5 h-5" />
        <h3 className="font-semibold text-lg">Estimated ROI</h3>
      </div>
      <p className="text-3xl font-bold">
        ${data.estimated_cost_saved_usd.toLocaleString("en-US", { minimumFractionDigits: 0 })}
      </p>
      <p className="text-blue-200 text-sm mt-1">estimated savings this period</p>
      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-blue-500/30">
        <div>
          <p className="text-2xl font-bold">{data.estimated_hours_saved}h</p>
          <p className="text-blue-200 text-xs">hours saved</p>
        </div>
        <div>
          <p className="text-2xl font-bold">{data.assets_processed}</p>
          <p className="text-blue-200 text-xs">assets processed by AI</p>
        </div>
      </div>
    </div>
  );
}
