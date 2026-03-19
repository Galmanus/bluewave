import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

// --- Webhooks ---

export interface WebhookData {
  id: string;
  name: string;
  url: string;
  events: string;
  is_active: boolean;
  created_at: string;
}

export function useWebhooks() {
  return useQuery<WebhookData[]>({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const { data } = await api.get("/webhooks");
      return data;
    },
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      name: string;
      url: string;
      secret?: string;
      events?: string;
    }) => {
      const { data } = await api.post("/webhooks", body);
      return data as WebhookData;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: {
      id: string;
      name?: string;
      url?: string;
      events?: string;
      is_active?: boolean;
    }) => {
      const { data } = await api.patch(`/webhooks/${id}`, body);
      return data as WebhookData;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/webhooks/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

// --- API Keys ---

export interface APIKeyData {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface APIKeyCreated extends APIKeyData {
  key: string;
  message: string;
}

export function useAPIKeys() {
  return useQuery<APIKeyData[]>({
    queryKey: ["api-keys"],
    queryFn: async () => {
      const { data } = await api.get("/api-keys");
      return data;
    },
  });
}

export function useCreateAPIKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string }) => {
      const { data } = await api.post("/api-keys", body);
      return data as APIKeyCreated;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useRevokeAPIKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api-keys/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}
