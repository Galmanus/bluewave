import { Activity, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

interface AIQualityData {
  caption_quality: {
    total_actions: number;
    avg_tokens: number;
  };
  hashtags_quality: {
    total_actions: number;
    avg_tokens: number;
  };
  compliance_quality: {
    total_actions: number;
    avg_tokens: number;
    total_checked: number;
    fallback_rate: number;
  };
}

function StatusDot({ value, thresholds }: { value: number; thresholds: [number, number] }) {
  const [warn, danger] = thresholds;
  if (value >= danger) return <XCircle className="w-4 h-4 text-red-500" />;
  if (value >= warn) return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
  return <CheckCircle className="w-4 h-4 text-green-500" />;
}

export default function AIQualityCard({ data }: { data: AIQualityData }) {
  const totalActions =
    data.caption_quality.total_actions +
    data.hashtags_quality.total_actions +
    data.compliance_quality.total_actions;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-purple-600" />
        <h3 className="font-semibold text-lg text-gray-900 dark:text-white">AI Quality</h3>
      </div>

      <p className="text-3xl font-bold text-gray-900 dark:text-white">{totalActions}</p>
      <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">total AI actions this period</p>

      <div className="space-y-3">
        {/* Captions */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">Captions</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {data.caption_quality.total_actions}
            </span>
            <span className="text-xs text-gray-500">
              avg {data.caption_quality.avg_tokens} tokens
            </span>
          </div>
        </div>

        {/* Hashtags */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">Hashtags</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {data.hashtags_quality.total_actions}
            </span>
            <span className="text-xs text-gray-500">
              avg {data.hashtags_quality.avg_tokens} tokens
            </span>
          </div>
        </div>

        {/* Compliance */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-300">Compliance</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {data.compliance_quality.total_actions}
            </span>
          </div>
        </div>

        {/* Compliance fallback rate */}
        {data.compliance_quality.total_checked > 0 && (
          <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
            <span className="text-sm text-gray-600 dark:text-gray-300">Compliance fallback rate</span>
            <div className="flex items-center gap-1">
              <StatusDot value={data.compliance_quality.fallback_rate} thresholds={[5, 15]} />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {data.compliance_quality.fallback_rate}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
