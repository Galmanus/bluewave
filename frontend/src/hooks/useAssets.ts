import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

export interface Asset {
  id: string;
  tenant_id: string;
  uploaded_by: string;
  file_path: string;
  file_type: string;
  file_size: number;
  caption: string | null;
  hashtags: string[] | null;
  status: "draft" | "pending_approval" | "approved";
  rejection_comment: string | null;
  compliance_score: number | null;
  compliance_issues: Array<{
    severity: string;
    category: string;
    message: string;
    suggestion: string;
  }> | null;
  created_at: string;
  updated_at: string;
}

interface AssetListResponse {
  items: Asset[];
  total: number;
  page: number;
  size: number;
}

export function useAssets(
  status?: string | null,
  page = 1,
  size = 20,
  search?: string,
) {
  return useQuery<AssetListResponse>({
    queryKey: ["assets", { status, page, size, search }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, size };
      if (status) params.status = status;
      if (search) params.q = search;
      const { data } = await api.get("/assets", { params });
      return data;
    },
  });
}

interface AssetCounts {
  draft: number;
  pending_approval: number;
  approved: number;
  total: number;
}

export function useAssetCounts() {
  return useQuery<AssetCounts>({
    queryKey: ["asset-counts"],
    queryFn: async () => {
      const { data } = await api.get("/assets/counts");
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function getAssetFileUrl(assetId: string): string {
  return `/api/v1/assets/${assetId}/file`;
}

export function getAssetAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function useAsset(id: string | undefined) {
  return useQuery<Asset>({
    queryKey: ["asset", id],
    queryFn: async () => {
      const { data } = await api.get(`/assets/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useUploadAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/assets", form);
      return data as Asset;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export function useUpdateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      caption,
      hashtags,
    }: {
      id: string;
      caption?: string;
      hashtags?: string[];
    }) => {
      const { data } = await api.patch(`/assets/${id}`, { caption, hashtags });
      return data as Asset;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["asset", vars.id] });
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export function useSubmitAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/assets/${id}/submit`);
      return data as Asset;
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["asset", id] });
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export function useApproveAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/assets/${id}/approve`);
      return data as Asset;
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["asset", id] });
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export function useRejectAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment: string }) => {
      const { data } = await api.post(`/assets/${id}/reject`, { comment });
      return data as Asset;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["asset", vars.id] });
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/assets/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}
