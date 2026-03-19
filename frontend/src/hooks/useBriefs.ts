import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

interface Brief {
  id: string;
  prompt: string;
  brief_content: Record<string, unknown> | null;
  suggested_asset_ids: string[] | null;
  status: string;
  cost_millicents: number;
  created_at: string;
}

export function useBriefs() {
  return useQuery<Brief[]>({
    queryKey: ["briefs"],
    queryFn: () => api.get("/briefs").then(r => r.data),
  });
}

export function useBrief(briefId: string) {
  return useQuery<Brief>({
    queryKey: ["briefs", briefId],
    queryFn: () => api.get(`/briefs/${briefId}`).then(r => r.data),
    enabled: !!briefId,
  });
}

export function useCreateBrief() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { prompt: string }) =>
      api.post("/briefs", data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["briefs"] }),
  });
}
