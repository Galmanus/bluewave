import { useState } from "react";
import { Lightbulb, Loader2, Plus, ChevronDown, ChevronRight } from "lucide-react";
import { useBriefs, useCreateBrief } from "../hooks/useBriefs";

export default function BriefsPage() {
  const { data: briefs = [], isLoading } = useBriefs();
  const createBrief = useCreateBrief();
  const [prompt, setPrompt] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleCreate = () => {
    if (!prompt.trim()) return;
    createBrief.mutate({ prompt: prompt.trim() });
    setPrompt("");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Lightbulb className="w-6 h-6 text-amber-500" />
        <h1 className="text-2xl font-bold">Content Briefs</h1>
        <span className="text-sm text-gray-500">$1.00 per brief</span>
      </div>

      {/* Create new brief */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4">
        <label className="block text-sm font-medium mb-2">Describe your campaign</label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="e.g., I need 5 posts for a summer beach campaign targeting young adults, lifestyle tone, Instagram and TikTok..."
          className="w-full h-28 px-3 py-2 border rounded-md dark:bg-gray-800 dark:border-gray-700 text-sm resize-none"
        />
        <button
          onClick={handleCreate}
          disabled={!prompt.trim() || createBrief.isPending}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {createBrief.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Generate Brief
        </button>
      </div>

      {/* Briefs list */}
      {isLoading ? (
        <div className="text-center py-10 text-gray-500">Loading briefs...</div>
      ) : briefs.length === 0 ? (
        <div className="text-center py-10 text-gray-500">No briefs yet. Create your first one above.</div>
      ) : (
        <div className="space-y-3">
          {briefs.map(brief => (
            <div key={brief.id} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700">
              <button
                onClick={() => setExpandedId(expandedId === brief.id ? null : brief.id)}
                className="w-full p-4 flex items-center justify-between text-left"
              >
                <div>
                  <p className="font-medium text-sm truncate max-w-xl">{brief.prompt}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {brief.status === "generating" && "Generating..."}
                    {brief.status === "completed" && "Completed"}
                    {brief.status === "failed" && "Failed"}
                    {" — "}{new Date(brief.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    brief.status === "completed" ? "bg-green-100 text-green-800" :
                    brief.status === "generating" ? "bg-yellow-100 text-yellow-800" :
                    "bg-red-100 text-red-800"
                  }`}>
                    {brief.status}
                  </span>
                  {expandedId === brief.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
              </button>
              {expandedId === brief.id && brief.brief_content && (
                <div className="px-4 pb-4 border-t dark:border-gray-700 pt-3">
                  {brief.brief_content.campaign_overview && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium mb-1">Campaign Overview</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{String(brief.brief_content.campaign_overview)}</p>
                    </div>
                  )}
                  {Array.isArray(brief.brief_content.content_pieces) && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium mb-1">Content Pieces</h4>
                      <div className="space-y-2">
                        {(brief.brief_content.content_pieces as Array<Record<string, string>>).map((piece, i) => (
                          <div key={i} className="bg-gray-50 dark:bg-gray-800 rounded p-2 text-sm">
                            <p className="font-medium">{piece.title}</p>
                            <p className="text-gray-600 dark:text-gray-400 mt-1">{piece.caption_draft}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(brief.brief_content.hashtag_strategy) && (
                    <div>
                      <h4 className="text-sm font-medium mb-1">Hashtag Strategy</h4>
                      <div className="flex flex-wrap gap-1">
                        {(brief.brief_content.hashtag_strategy as string[]).map((tag, i) => (
                          <span key={i} className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded text-xs">{tag}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
