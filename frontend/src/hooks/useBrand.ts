import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

export interface BrandGuideline {
  id: string;
  primary_colors: string[] | null;
  secondary_colors: string[] | null;
  fonts: string[] | null;
  logo_urls: string[] | null;
  tone_description: string | null;
  dos: string[] | null;
  donts: string[] | null;
  custom_rules: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplianceIssue {
  severity: "error" | "warning" | "info";
  category: string;
  message: string;
  suggestion: string;
}

export interface ComplianceResult {
  score: number;
  passed: boolean;
  summary: string;
  issues: ComplianceIssue[];
}

export function useBrandGuidelines() {
  return useQuery<BrandGuideline | null>({
    queryKey: ["brand-guidelines"],
    queryFn: async () => {
      const { data } = await api.get("/brand/guidelines");
      return data;
    },
  });
}

export function useUpdateBrandGuidelines() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<BrandGuideline>) => {
      const { data } = await api.put("/brand/guidelines", body);
      return data as BrandGuideline;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brand-guidelines"] }),
  });
}

export function useComplianceCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assetId: string) => {
      const { data } = await api.post(`/brand/check/${assetId}`);
      return data as ComplianceResult;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["asset"] });
    },
  });
}
