import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import api from "../lib/api";

interface Version {
  id: string;
  version_number: number;
  file_type: string;
  file_size: number;
  caption: string | null;
  comment: string | null;
  created_at: string;
}

export function useVersions(assetId: string) {
  return useQuery<Version[]>({
    queryKey: ["versions", assetId],
    queryFn: () => api.get(`/assets/${assetId}/versions`).then(r => r.data),
    enabled: !!assetId,
  });
}

export function useRestoreVersion(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (versionId: string) =>
      api.post(`/assets/${assetId}/versions/${versionId}/restore`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["versions", assetId] });
      qc.invalidateQueries({ queryKey: ["asset", assetId] });
    },
  });
}
