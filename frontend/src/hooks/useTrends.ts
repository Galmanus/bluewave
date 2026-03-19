import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

export interface Trend {
  id: string;
  keyword: string;
  source: string;
  volume: number;
  volume_change_pct: number;
  sentiment_score: number | null;
  region: string;
  category: string | null;
  relevance_score: number;
  ai_suggestion: string | null;
  ai_caption_draft: string | null;
  ai_hashtags: string[] | null;
  created_at: string;
}

export function useTrends(activeOnly = true) {
  return useQuery<Trend[]>({
    queryKey: ["trends", { activeOnly }],
    queryFn: async () => {
      const { data } = await api.get("/trends", {
        params: { active_only: activeOnly, limit: 20 },
      });
      return data;
    },
  });
}

export function useTrend(id: string | undefined) {
  return useQuery<Trend>({
    queryKey: ["trend", id],
    queryFn: async () => {
      const { data } = await api.get(`/trends/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useDiscoverTrends() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      keywords?: string[];
      region?: string;
      niche?: string;
    }) => {
      const { data } = await api.post("/trends/discover", body);
      return data as { discovered: number; trends: Trend[] };
    },
    onSuccess: () => {
      // Refetch after a delay to get background-discovered trends
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["trends"] });
      }, 5000);
    },
  });
}

export function useCleanupExpiredTrends() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete("/trends/expired");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trends"] }),
  });
}
