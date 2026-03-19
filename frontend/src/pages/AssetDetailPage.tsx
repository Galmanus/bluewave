import { FormEvent, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Video,
  Send,
  Check,
  X as XIcon,
  Trash2,
  FileText,
  ShieldCheck,
  AlertTriangle,
  Info,
  Copy,
} from "lucide-react";
import {
  useAsset,
  useUpdateAsset,
  useSubmitAsset,
  useApproveAsset,
  useRejectAsset,
  useDeleteAsset,
  getAssetFileUrl,
} from "../hooks/useAssets";
import { useComplianceCheck } from "../hooks/useBrand";
import { useAuth } from "../contexts/AuthContext";
import CommentsSection from "../components/CommentsSection";
import VersionHistory from "../components/VersionHistory";
import { Button } from "../components/ui/Button";
import { Input, Textarea } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { ConfirmDialog } from "../components/ui/Dialog";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "draft" | "pending_approval" | "approved"> = {
  draft: "draft",
  pending_approval: "pending_approval",
  approved: "approved",
};

const SEVERITY_ICON: Record<string, typeof AlertTriangle> = {
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info,
};

const SEVERITY_COLOR: Record<string, string> = {
  error: "text-danger",
  warning: "text-warning",
  info: "text-accent",
};

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
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
  const displayHashtags =
    hashtags ?? (asset?.hashtags ? asset.hashtags.join(", ") : "");

  if (isLoading) {
    return (
      <div className="space-y-lg">
        <div className="h-5 w-32 animate-pulse rounded bg-border-subtle" />
        <div className="grid gap-xl lg:grid-cols-5">
          <div className="lg:col-span-3 h-80 animate-pulse rounded-lg bg-border-subtle" />
          <div className="lg:col-span-2 space-y-lg">
            <div className="h-8 w-24 animate-pulse rounded bg-border-subtle" />
            <div className="h-20 animate-pulse rounded bg-border-subtle" />
            <div className="h-10 animate-pulse rounded bg-border-subtle" />
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
        <Button asChild variant="secondary">
          <Link to="/assets">Back to assets</Link>
        </Button>
      </div>
    );
  }

  const isEditor = user && ["admin", "editor"].includes(user.role);
  const isAdmin = user?.role === "admin";

  function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    const payload: { id: string; caption?: string; hashtags?: string[] } = { id };
    if (caption !== null) payload.caption = caption;
    if (hashtags !== null)
      payload.hashtags = hashtags.split(",").map((h) => h.trim()).filter(Boolean);
    updateAsset.mutate(payload);
  }

  function handleComplianceCheck() {
    if (!id) return;
    complianceCheck.mutate(id, {
      onSuccess: () => {
        refetch();
        toast.success("Compliance check complete");
      },
    });
  }

  function copyHashtags() {
    if (asset?.hashtags) {
      navigator.clipboard.writeText(asset.hashtags.join(" "));
      toast.success("Hashtags copied!");
    }
  }

  const complianceScore = asset.compliance_score;
  const complianceColor =
    complianceScore === null ? "text-text-tertiary" :
    complianceScore >= 90 ? "text-success" :
    complianceScore >= 70 ? "text-warning" : "text-danger";

  return (
    <div>
      <Link
        to="/assets"
        className="mb-xl inline-flex items-center gap-1.5 text-body text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
        Back to assets
      </Link>

      <div className="grid gap-xl lg:grid-cols-5">
        {/* Preview — 60% */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="lg:col-span-3 flex items-center justify-center rounded-xl border border-border bg-surface-elevated overflow-hidden"
          style={{ minHeight: 320 }}
        >
          {asset.file_type.startsWith("image/") ? (
            <img
              src={getAssetFileUrl(asset.id)}
              alt={asset.caption || "Asset preview"}
              className="max-h-[500px] w-full object-contain"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = "none";
              }}
            />
          ) : (
            <Video className="h-20 w-20 text-text-tertiary" strokeWidth={0.8} />
          )}
        </motion.div>

        {/* Metadata — 40% */}
        <motion.div
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 space-y-xl"
        >
          {/* Status + Compliance */}
          <div className="flex items-center gap-3 flex-wrap">
            <Badge variant={STATUS_VARIANT[asset.status]} dot>
              {asset.status.replace("_", " ")}
            </Badge>
            {complianceScore !== null && (
              <span className={`inline-flex items-center gap-1 text-body-medium ${complianceColor}`}>
                <ShieldCheck className="h-4 w-4" />
                {complianceScore}/100
              </span>
            )}
            <span className="text-caption text-text-tertiary font-mono">
              {asset.file_type} &middot; {(asset.file_size / 1024).toFixed(1)} KB
            </span>
          </div>

          {/* Rejection */}
          {asset.rejection_comment && (
            <div className="rounded-lg border border-danger/20 bg-danger-subtle p-md text-body text-danger">
              <strong>Rejected:</strong> {asset.rejection_comment}
            </div>
          )}

          {/* Compliance Issues */}
          {asset.compliance_issues && asset.compliance_issues.length > 0 && (
            <div className="rounded-lg border border-border bg-surface p-md space-y-2">
              <p className="text-body-medium text-text-primary flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" />
                Compliance Issues
              </p>
              {asset.compliance_issues.map((issue, i) => {
                const Icon = SEVERITY_ICON[issue.severity] || Info;
                const color = SEVERITY_COLOR[issue.severity] || "text-text-secondary";
                return (
                  <div key={i} className="flex items-start gap-2 text-caption">
                    <Icon className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${color}`} />
                    <div>
                      <span className="text-text-primary">{issue.message}</span>
                      {issue.suggestion && (
                        <p className="text-text-tertiary mt-0.5">{issue.suggestion}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Edit form */}
          <form onSubmit={handleSave} className="space-y-lg">
            <Textarea
              label="Caption"
              rows={3}
              value={displayCaption}
              onChange={(e) => setCaption(e.target.value)}
              disabled={!isEditor}
              placeholder="AI-generated caption..."
            />
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-body-medium text-text-primary">Hashtags</label>
                {asset.hashtags && asset.hashtags.length > 0 && (
                  <button
                    type="button"
                    onClick={copyHashtags}
                    className="inline-flex items-center gap-1 text-caption text-text-tertiary hover:text-text-primary transition-colors"
                  >
                    <Copy className="h-3 w-3" />
                    Copy
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
                Save changes
              </Button>
            )}
          </form>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 border-t border-border-subtle pt-xl">
            {isEditor && asset.status === "draft" && (
              <Button
                variant="secondary"
                onClick={() => submitAsset.mutate(asset.id)}
                loading={submitAsset.isPending}
              >
                <Send className="h-4 w-4" strokeWidth={1.5} />
                Submit for approval
              </Button>
            )}
            {isAdmin && asset.status === "pending_approval" && (
              <>
                {asset.compliance_score !== null && asset.compliance_score < 70 && (
                  <p className="w-full text-caption text-danger flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Compliance score too low ({asset.compliance_score}/100). Fix issues before approving.
                  </p>
                )}
                <Button
                  onClick={() => approveAsset.mutate(asset.id)}
                  loading={approveAsset.isPending}
                  disabled={asset.compliance_score !== null && asset.compliance_score < 70}
                >
                  <Check className="h-4 w-4" strokeWidth={1.5} />
                  Approve
                </Button>
                <Button
                  variant="danger-outline"
                  onClick={() => setShowRejectForm(true)}
                >
                  <XIcon className="h-4 w-4" strokeWidth={1.5} />
                  Reject
                </Button>
              </>
            )}
            {isEditor && (
              <Button
                variant="secondary"
                onClick={handleComplianceCheck}
                loading={complianceCheck.isPending}
              >
                <ShieldCheck className="h-4 w-4" strokeWidth={1.5} />
                Check Compliance
              </Button>
            )}
            {isAdmin && (
              <Button
                variant="ghost"
                onClick={() => setDeleteOpen(true)}
                className="text-danger hover:text-danger"
              >
                <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                Delete
              </Button>
            )}
          </div>

          {/* Reject form */}
          {showRejectForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="space-y-3 rounded-lg border border-danger/20 bg-danger-subtle p-md"
            >
              <Textarea
                rows={2}
                placeholder="Reason for rejection..."
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    if (rejectComment.trim()) {
                      rejectAsset.mutate({ id: asset.id, comment: rejectComment });
                      setShowRejectForm(false);
                      setRejectComment("");
                    }
                  }}
                  loading={rejectAsset.isPending}
                  disabled={!rejectComment.trim()}
                >
                  Confirm reject
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowRejectForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* Version History */}
      <div className="mt-xl">
        <VersionHistory assetId={id!} />
      </div>

      {/* Comments */}
      <div className="mt-xl">
        <CommentsSection assetId={id!} />
      </div>

      {/* Delete dialog */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete asset"
        description="This action cannot be undone. The asset and all its metadata will be permanently removed."
        confirmLabel="Delete"
        variant="danger"
        loading={deleteAsset.isPending}
        onConfirm={() =>
          deleteAsset.mutate(asset.id, {
            onSuccess: () => navigate("/assets"),
          })
        }
      />
    </div>
  );
}
