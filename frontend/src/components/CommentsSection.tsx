import { useState } from "react";
import { MessageSquare, Check, Send } from "lucide-react";
import { useComments, useCreateComment, useResolveComment } from "../hooks/useComments";

interface Props {
  assetId: string;
}

export default function CommentsSection({ assetId }: Props) {
  const { data: comments = [], isLoading } = useComments(assetId);
  const createComment = useCreateComment(assetId);
  const resolveComment = useResolveComment(assetId);
  const [body, setBody] = useState("");

  const handleSubmit = () => {
    if (!body.trim()) return;
    createComment.mutate({ body: body.trim() });
    setBody("");
  };

  const unresolvedCount = comments.filter(c => !c.is_resolved && !c.parent_id).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-gray-500" />
        <h3 className="font-medium">Comments</h3>
        {unresolvedCount > 0 && (
          <span className="px-2 py-0.5 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
            {unresolvedCount} open
          </span>
        )}
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading comments...</p>
      ) : comments.length === 0 ? (
        <p className="text-sm text-gray-500">No comments yet. Start the conversation.</p>
      ) : (
        <div className="space-y-3">
          {comments
            .filter(c => !c.parent_id)
            .map(comment => (
              <div
                key={comment.id}
                className={`rounded-lg border p-3 ${
                  comment.is_resolved
                    ? "border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-900/10"
                    : "border-gray-200 dark:border-gray-700"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-sm font-medium">{comment.user_name || "User"}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {new Date(comment.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {!comment.is_resolved && (
                    <button
                      onClick={() => resolveComment.mutate(comment.id)}
                      className="text-xs text-gray-500 hover:text-green-600 flex items-center gap-1"
                      title="Mark as resolved"
                    >
                      <Check className="w-3 h-3" /> Resolve
                    </button>
                  )}
                </div>
                <p className="text-sm mt-1 text-gray-700 dark:text-gray-300">{comment.body}</p>

                {/* Replies */}
                {comments
                  .filter(r => r.parent_id === comment.id)
                  .map(reply => (
                    <div key={reply.id} className="ml-4 mt-2 pl-3 border-l-2 border-gray-200 dark:border-gray-700">
                      <span className="text-sm font-medium">{reply.user_name || "User"}</span>
                      <span className="text-xs text-gray-400 ml-2">
                        {new Date(reply.created_at).toLocaleDateString()}
                      </span>
                      <p className="text-sm mt-1 text-gray-700 dark:text-gray-300">{reply.body}</p>
                    </div>
                  ))}
              </div>
            ))}
        </div>
      )}

      {/* New comment input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={body}
          onChange={e => setBody(e.target.value)}
          placeholder="Add a comment..."
          className="flex-1 px-3 py-2 border rounded-md text-sm dark:bg-gray-800 dark:border-gray-700"
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
        />
        <button
          onClick={handleSubmit}
          disabled={!body.trim() || createComment.isPending}
          className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
