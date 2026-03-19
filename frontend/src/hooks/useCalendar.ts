import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

interface ScheduledPost {
  id: string;
  asset_id: string;
  scheduled_at: string;
  channel: string;
  caption_override: string | null;
  hashtags_override: string[] | null;
  status: string;
  published_at: string | null;
  external_url: string | null;
  error_message: string | null;
  created_at: string;
}

export function useCalendar(start: string, end: string) {
  return useQuery<ScheduledPost[]>({
    queryKey: ["calendar", start, end],
    queryFn: () => api.get(`/calendar?start=${start}&end=${end}`).then(r => r.data),
    enabled: !!start && !!end,
  });
}

export function useSchedulePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { asset_id: string; scheduled_at: string; channel: string; caption_override?: string }) =>
      api.post("/calendar", data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar"] }),
  });
}

export function useCancelPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => api.delete(`/calendar/${postId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar"] }),
  });
}

export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => api.post(`/calendar/${postId}/publish`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar"] }),
  });
}
