import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

interface Comment {
  id: string;
  asset_id: string;
  user_id: string;
  parent_id: string | null;
  body: string;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
  user_name: string | null;
}

export function useComments(assetId: string) {
  return useQuery<Comment[]>({
    queryKey: ["comments", assetId],
    queryFn: () => api.get(`/assets/${assetId}/comments`).then(r => r.data),
    enabled: !!assetId,
  });
}

export function useCreateComment(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { body: string; parent_id?: string }) =>
      api.post(`/assets/${assetId}/comments`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["comments", assetId] }),
  });
}

export function useResolveComment(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      api.post(`/assets/${assetId}/comments/${commentId}/resolve`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["comments", assetId] }),
  });
}
