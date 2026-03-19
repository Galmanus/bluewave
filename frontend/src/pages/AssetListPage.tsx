import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Upload, ImageIcon, Video, Search, ShieldCheck } from "lucide-react";
import { useAssets, getAssetFileUrl } from "../hooks/useAssets";
import { useAuth } from "../contexts/AuthContext";
import SelectionToolbar from "../components/SelectionToolbar";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";

const TABS = [
  { label: "All", value: null },
  { label: "Draft", value: "draft" },
  { label: "Pending", value: "pending_approval" },
  { label: "Approved", value: "approved" },
] as const;

const STATUS_VARIANT: Record<string, "draft" | "pending_approval" | "approved"> = {
  draft: "draft",
  pending_approval: "pending_approval",
  approved: "approved",
};

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ComplianceBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const color = score >= 90 ? "text-success" : score >= 70 ? "text-warning" : "text-danger";
  return (
    <span className={`inline-flex items-center gap-1 text-caption font-medium ${color}`}>
      <ShieldCheck className="h-3 w-3" />
      {score}
    </span>
  );
}

export default function AssetListPage() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const { data, isLoading } = useAssets(statusFilter, page, 20, search || undefined);
  const { user } = useAuth();

  const totalPages = data ? Math.ceil(data.total / data.size) : 1;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-display text-text-primary">Assets</h1>
          {data && (
            <Badge variant="default">{data.total}</Badge>
          )}
        </div>
        {user && ["admin", "editor"].includes(user.role) && (
          <Button asChild>
            <Link to="/assets/upload">
              <Upload className="h-4 w-4" strokeWidth={1.5} />
              Upload
            </Link>
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="mt-lg">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(searchInput);
            setPage(1);
          }}
          className="relative max-w-md"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search captions, filenames..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full rounded-md border border-border bg-surface pl-10 pr-4 py-2 text-body text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-background"
          />
          {search && (
            <button
              type="button"
              onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-caption text-text-tertiary hover:text-text-primary"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Tabs */}
      <div className="mt-lg flex gap-1 border-b border-border-subtle">
        {TABS.map((tab) => {
          const isActive = statusFilter === tab.value;
          return (
            <button
              key={tab.label}
              onClick={() => {
                setStatusFilter(tab.value);
                setPage(1);
              }}
              className="relative px-4 py-2.5 text-body-medium transition-colors"
            >
              <span
                className={
                  isActive ? "text-accent" : "text-text-tertiary hover:text-text-secondary"
                }
              >
                {tab.label}
              </span>
              {isActive && (
                <motion.div
                  layoutId="asset-tab-indicator"
                  className="absolute inset-x-0 -bottom-px h-0.5 bg-accent"
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="mt-xl grid grid-cols-1 gap-lg sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-52 animate-pulse rounded-lg bg-border-subtle"
            />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="mt-xl grid grid-cols-1 gap-lg sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.items.map((asset, i) => (
              <motion.div
                key={asset.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04, duration: 0.2 }}
              >
                <Link to={`/assets/${asset.id}`}>
                  <Card className="group cursor-pointer overflow-hidden hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
                    {/* Thumbnail */}
                    <div className="relative h-32 bg-border-subtle overflow-hidden">
                      {/* Selection checkbox */}
                      <label
                        className="absolute top-2 left-2 z-10"
                        onClick={e => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(asset.id)}
                          onChange={e => {
                            e.stopPropagation();
                            e.preventDefault();
                            setSelectedIds(prev =>
                              prev.includes(asset.id)
                                ? prev.filter(sid => sid !== asset.id)
                                : [...prev, asset.id]
                            );
                          }}
                          className="h-4 w-4 rounded border-gray-300 text-accent focus:ring-accent cursor-pointer"
                        />
                      </label>
                      {asset.file_type.startsWith("image/") ? (
                        <img
                          src={getAssetFileUrl(asset.id)}
                          alt={asset.caption || "Asset preview"}
                          className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
                          loading="lazy"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = "none";
                            target.parentElement!.classList.add("flex", "items-center", "justify-center");
                            const icon = document.createElement("div");
                            icon.innerHTML = '<svg class="h-8 w-8 text-text-tertiary" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>';
                            target.parentElement!.appendChild(icon.firstChild!);
                          }}
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-text-tertiary group-hover:text-accent transition-colors">
                          <Video className="h-8 w-8" strokeWidth={1} />
                        </div>
                      )}
                    </div>
                    {/* Info */}
                    <div className="p-md space-y-2">
                      <p className="truncate text-body-medium text-text-primary">
                        {asset.caption || "No caption"}
                      </p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-caption text-text-tertiary font-mono">
                            {formatSize(asset.file_size)}
                          </span>
                          <ComplianceBadge score={asset.compliance_score} />
                        </div>
                        <Badge
                          variant={STATUS_VARIANT[asset.status]}
                          dot
                        >
                          {asset.status.replace("_", " ")}
                        </Badge>
                      </div>
                    </div>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-xl flex items-center justify-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-body text-text-secondary">
                {page} / {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      ) : (
        <div className="mt-3xl flex flex-col items-center gap-3 text-center">
          <ImageIcon className="h-12 w-12 text-text-tertiary" strokeWidth={1} />
          <p className="text-body text-text-secondary">
            {search ? `No assets matching "${search}"` : "No assets found"}
          </p>
          {user && ["admin", "editor"].includes(user.role) && !search && (
            <Button asChild variant="secondary">
              <Link to="/assets/upload">Upload your first asset</Link>
            </Button>
          )}
        </div>
      )}

      <SelectionToolbar
        selectedIds={selectedIds}
        onClear={() => setSelectedIds([])}
      />
    </div>
  );
}
