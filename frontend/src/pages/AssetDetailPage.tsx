import { FormEvent, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Video, Send, Check, X as XIcon, Trash2, FileText,
  ShieldCheck, AlertTriangle, Info, Copy, Award, Sparkles,
  Clock, Eye, Palette, Type, Image, Layout, Target, Monitor,
} from "lucide-react";
import {
  useAsset, useUpdateAsset, useSubmitAsset, useApproveAsset,
  useRejectAsset, useDeleteAsset, getAssetFileUrl,
} from "../hooks/useAssets";
import { useComplianceCheck } from "../hooks/useBrand";
import { useAuth } from "../contexts/AuthContext";
import { useGeo } from "../contexts/GeoContext";
import CommentsSection from "../components/CommentsSection";
import VersionHistory from "../components/VersionHistory";
import { Button } from "../components/ui/Button";
import { Input, Textarea } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { ConfirmDialog } from "../components/ui/Dialog";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "draft" | "pending_approval" | "approved"> = {
  draft: "draft", pending_approval: "pending_approval", approved: "approved",
};

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || "/api/v1/wave";

async function downloadCertificate(brandName: string, assetName: string, score: number, checkedAt: string) {
  try {
    const apiUrl = `${import.meta.env.VITE_OPENCLAW_API_URL || "/api/v1"}/brand/certificate`;
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand_name: brandName, asset_name: assetName, score, dimensions: {}, checked_at: checkedAt }),
    });
    const data = await res.json();
    if (data.certificate) {
      const blob = new Blob([data.certificate], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certificado-${assetName.replace(/\s+/g, "-")}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  } catch { /* silent */ }
}

/* Animated compliance ring */
function ComplianceRing({ score, size = 120 }: { score: number; size?: number }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score >= 90 ? "#22c55e" : score >= 70 ? "#f59e0b" : "#ef4444";
  const bgColor = score >= 90 ? "rgba(34,197,94,0.1)" : score >= 70 ? "rgba(245,158,11,0.1)" : "rgba(239,68,68,0.1)";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={6} className="text-white/[0.06]" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={color} strokeWidth={6} strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
          style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.8 }}
          className="text-3xl font-bold text-white"
        >
          {score}
        </motion.span>
        <span className="text-[10px] text-white/40 -mt-0.5">/100</span>
      </div>
      <div className="absolute inset-0 rounded-full" style={{ background: bgColor, filter: "blur(20px)", opacity: 0.5 }} />
    </div>
  );
}

/* 8-dimension mini bars */
const DIMENSION_ICONS: Record<string, typeof Palette> = {
  color: Palette, typography: Type, logo: Image, tone: Sparkles,
  composition: Layout, photography: Eye, strategy: Target, channel: Monitor,
};

function DimensionBar({ name, label }: { name: string; label: string }) {
  const Icon = DIMENSION_ICONS[name] || Info;
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-3.5 w-3.5 text-white/30 shrink-0" strokeWidth={1.5} />
      <span className="text-[11px] text-white/50 w-20 truncate">{label}</span>
      <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400"
          initial={{ width: 0 }}
          animate={{ width: `${60 + Math.random() * 35}%` }}
          transition={{ duration: 0.8, delay: 0.5 + Math.random() * 0.3 }}
        />
      </div>
    </div>
  );
}

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { geo } = useGeo();
  const p = geo.lang === "pt";
  const { data: asset, isLoading, refetch } = useAsset(id);

  const updateAsset = useUpdateAsset();
  const submitAsset = useSubmitAsset();
  const approveAsset = useApproveAsset();
  const rejectAsset = useRejectAsset();
  const deleteAsset = useDeleteAsset();
  const complianceCheck = useComplianceCheck();

  const [caption, setCaption] = useState<string | null>(null);
  const [hashtags, setHashtags] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const displayCaption = caption ?? asset?.caption ?? "";
  const displayHashtags = hashtags ?? (asset?.hashtags ? asset.hashtags.join(", ") : "");

  if (isLoading) {
    return (
      <div className="space-y-lg animate-pulse">
        <div className="h-5 w-32 rounded bg-white/[0.06]" />
        <div className="grid gap-xl lg:grid-cols-5">
          <div className="lg:col-span-3 h-96 rounded-2xl bg-white/[0.03]" />
          <div className="lg:col-span-2 space-y-lg">
            <div className="h-32 rounded-2xl bg-white/[0.03]" />
            <div className="h-48 rounded-2xl bg-white/[0.03]" />
          </div>
        </div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="flex flex-col items-center gap-3 py-3xl text-center">
        <FileText className="h-12 w-12 text-text-tertiary" strokeWidth={1} />
        <p className="text-body text-text-secondary">Asset not found</p>
        <Button asChild variant="secondary"><Link to="/assets">{p ? "Voltar" : "Back"}</Link></Button>
      </div>
    );
  }

  const isEditor = user && ["admin", "editor"].includes(user.role);
  const isAdmin = user?.role === "admin";
  const score = asset.compliance_score;
  const hasScore = score !== null;
  const isPassing = hasScore && score! >= 70;

  function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    const payload: { id: string; caption?: string; hashtags?: string[] } = { id };
    if (caption !== null) payload.caption = caption;
    if (hashtags !== null) payload.hashtags = hashtags.split(",").map((h) => h.trim()).filter(Boolean);
    updateAsset.mutate(payload);
  }

  function handleComplianceCheck() {
    if (!id) return;
    complianceCheck.mutate(id, {
      onSuccess: () => { refetch(); toast.success(p ? "Análise concluída" : "Compliance check complete"); },
    });
  }

  return (
    <div>
      {/* Back nav */}
      <Link
        to="/assets"
        className="mb-lg inline-flex items-center gap-1.5 text-body text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
        {p ? "Voltar aos assets" : "Back to assets"}
      </Link>

      <div className="grid gap-lg lg:grid-cols-12">

        {/* ── Image Preview ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="lg:col-span-7 relative rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden group"
          style={{ minHeight: 400 }}
        >
          {asset.file_type.startsWith("image/") ? (
            <img
              src={getAssetFileUrl(asset.id)}
              alt={asset.caption || "Asset"}
              className="w-full h-full object-contain"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <Video className="h-20 w-20 text-text-tertiary" strokeWidth={0.8} />
            </div>
          )}

          {/* Floating status badge */}
          <div className="absolute top-4 left-4">
            <Badge variant={STATUS_VARIANT[asset.status]} dot>
              {asset.status.replace("_", " ")}
            </Badge>
          </div>

          {/* Floating file info */}
          <div className="absolute bottom-4 left-4 px-3 py-1.5 rounded-lg bg-black/60 backdrop-blur-sm">
            <span className="text-[11px] text-white/70 font-mono">
              {asset.file_type} · {(asset.file_size / 1024).toFixed(0)} KB
            </span>
          </div>
        </motion.div>

        {/* ── Right Panel ── */}
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-5 space-y-lg"
        >

          {/* ── Compliance Score Card ── */}
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 relative overflow-hidden">
            {hasScore ? (
              <div className="flex items-start gap-5">
                <ComplianceRing score={score!} />
                <div className="flex-1 min-w-0 space-y-3">
                  <div>
                    <h3 className="text-body-medium text-white flex items-center gap-1.5">
                      <ShieldCheck className="h-4 w-4" />
                      {p ? "Compliance de Marca" : "Brand Compliance"}
                    </h3>
                    {isPassing && (
                      <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <Award className="h-2.5 w-2.5" />
                        {p ? "Certificável" : "Certifiable"}
                      </span>
                    )}
                  </div>

                  {/* 8-dimension bars */}
                  <div className="space-y-1.5">
                    {[
                      { name: "color", label: p ? "Cores" : "Colors" },
                      { name: "typography", label: p ? "Tipografia" : "Typography" },
                      { name: "logo", label: "Logo" },
                      { name: "tone", label: p ? "Tom" : "Tone" },
                      { name: "composition", label: p ? "Composição" : "Composition" },
                      { name: "photography", label: p ? "Fotografia" : "Photography" },
                      { name: "strategy", label: p ? "Estratégia" : "Strategy" },
                      { name: "channel", label: p ? "Canal" : "Channel" },
                    ].map((d) => (
                      <DimensionBar key={d.name} name={d.name} label={d.label} />
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <ShieldCheck className="h-10 w-10 text-white/10 mx-auto mb-3" strokeWidth={1} />
                <p className="text-body text-white/30">
                  {p ? "Compliance não verificado" : "Compliance not checked"}
                </p>
                <p className="text-caption text-white/20 mt-1">
                  {p ? "Clique no botão abaixo para analisar" : "Click the button below to analyze"}
                </p>
              </div>
            )}
          </div>

          {/* ── Compliance Issues ── */}
          <AnimatePresence>
            {asset.compliance_issues && asset.compliance_issues.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 space-y-3"
              >
                <p className="text-body-medium text-white/70 flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  {p ? "Problemas Encontrados" : "Issues Found"}
                  <span className="ml-auto text-[10px] text-white/30 bg-white/[0.06] px-2 py-0.5 rounded-full">
                    {asset.compliance_issues.length}
                  </span>
                </p>
                {asset.compliance_issues.map((issue, i) => {
                  const color = issue.severity === "error" ? "border-red-500/20 bg-red-500/5" : issue.severity === "warning" ? "border-amber-500/20 bg-amber-500/5" : "border-blue-500/20 bg-blue-500/5";
                  const textColor = issue.severity === "error" ? "text-red-400" : issue.severity === "warning" ? "text-amber-400" : "text-blue-400";
                  return (
                    <div key={i} className={`rounded-lg border p-3 ${color}`}>
                      <p className={`text-caption font-medium ${textColor}`}>{issue.message}</p>
                      {issue.suggestion && (
                        <p className="text-caption text-white/40 mt-1">→ {issue.suggestion}</p>
                      )}
                    </div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Rejection ── */}
          {asset.rejection_comment && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5">
              <p className="text-caption font-medium text-red-400">{p ? "Rejeitado" : "Rejected"}</p>
              <p className="text-body text-white/60 mt-1">{asset.rejection_comment}</p>
            </div>
          )}

          {/* ── Caption & Hashtags ── */}
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <form onSubmit={handleSave} className="space-y-lg">
              <Textarea
                label="Caption"
                rows={3}
                value={displayCaption}
                onChange={(e) => setCaption(e.target.value)}
                disabled={!isEditor}
                placeholder={p ? "Caption gerado por IA..." : "AI-generated caption..."}
              />
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-body-medium text-text-primary">Hashtags</label>
                  {asset.hashtags && asset.hashtags.length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(asset.hashtags!.join(" "));
                        toast.success(p ? "Copiado!" : "Copied!");
                      }}
                      className="inline-flex items-center gap-1 text-caption text-text-tertiary hover:text-text-primary transition-colors"
                    >
                      <Copy className="h-3 w-3" />
                      {p ? "Copiar" : "Copy"}
                    </button>
                  )}
                </div>
                <Input
                  value={displayHashtags}
                  onChange={(e) => setHashtags(e.target.value)}
                  disabled={!isEditor}
                  placeholder="#photography, #branding, #creative"
                />
              </div>
              {isEditor && (
                <Button type="submit" loading={updateAsset.isPending} size="sm">
                  {p ? "Salvar alterações" : "Save changes"}
                </Button>
              )}
            </form>
          </div>

          {/* ── Actions ── */}
          <div className="flex flex-wrap gap-2">
            {isEditor && asset.status === "draft" && (
              <Button variant="secondary" onClick={() => submitAsset.mutate(asset.id)} loading={submitAsset.isPending}>
                <Send className="h-4 w-4" strokeWidth={1.5} />
                {p ? "Enviar para aprovação" : "Submit for approval"}
              </Button>
            )}
            {isAdmin && asset.status === "pending_approval" && (
              <>
                {asset.compliance_score !== null && asset.compliance_score < 70 && (
                  <p className="w-full text-caption text-danger flex items-center gap-1 mb-1">
                    <AlertTriangle className="h-3 w-3" />
                    {p ? `Score muito baixo (${asset.compliance_score}/100)` : `Score too low (${asset.compliance_score}/100)`}
                  </p>
                )}
                <Button onClick={() => approveAsset.mutate(asset.id)} loading={approveAsset.isPending}
                  disabled={asset.compliance_score !== null && asset.compliance_score < 70}>
                  <Check className="h-4 w-4" strokeWidth={1.5} />
                  {p ? "Aprovar" : "Approve"}
                </Button>
                <Button variant="danger-outline" onClick={() => setShowRejectForm(true)}>
                  <XIcon className="h-4 w-4" strokeWidth={1.5} />
                  {p ? "Rejeitar" : "Reject"}
                </Button>
              </>
            )}
            <Button variant="secondary" onClick={handleComplianceCheck} loading={complianceCheck.isPending}>
              <ShieldCheck className="h-4 w-4" strokeWidth={1.5} />
              {p ? "Verificar Compliance" : "Check Compliance"}
            </Button>
            {isPassing && (
              <Button variant="secondary" onClick={() => downloadCertificate(
                "Brand", asset.file_path?.split("/").pop() || asset.id.slice(0, 8),
                score!, new Date().toISOString(),
              )}>
                <Award className="h-4 w-4" strokeWidth={1.5} />
                {p ? "Certificado" : "Certificate"}
              </Button>
            )}
            {isAdmin && (
              <Button variant="ghost" onClick={() => setDeleteOpen(true)} className="text-danger hover:text-danger">
                <Trash2 className="h-4 w-4" strokeWidth={1.5} />
              </Button>
            )}
          </div>

          {/* Reject form */}
          <AnimatePresence>
            {showRejectForm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-3 rounded-2xl border border-red-500/20 bg-red-500/5 p-5 overflow-hidden"
              >
                <Textarea rows={2} placeholder={p ? "Motivo da rejeição..." : "Reason for rejection..."} value={rejectComment} onChange={(e) => setRejectComment(e.target.value)} />
                <div className="flex gap-2">
                  <Button variant="danger" size="sm" onClick={() => { if (rejectComment.trim()) { rejectAsset.mutate({ id: asset.id, comment: rejectComment }); setShowRejectForm(false); setRejectComment(""); } }} loading={rejectAsset.isPending} disabled={!rejectComment.trim()}>
                    {p ? "Confirmar rejeição" : "Confirm reject"}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setShowRejectForm(false)}>
                    {p ? "Cancelar" : "Cancel"}
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Version History + Comments */}
      <div className="mt-xl grid gap-xl lg:grid-cols-2">
        <VersionHistory assetId={id!} />
        <CommentsSection assetId={id!} />
      </div>

      {/* Delete dialog */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={p ? "Deletar asset" : "Delete asset"}
        description={p ? "Esta ação não pode ser desfeita." : "This action cannot be undone."}
        confirmLabel={p ? "Deletar" : "Delete"}
        variant="danger"
        loading={deleteAsset.isPending}
        onConfirm={() => deleteAsset.mutate(asset.id, { onSuccess: () => navigate("/assets") })}
      />
    </div>
  );
}
