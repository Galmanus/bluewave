import { FormEvent, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  Sparkles,
  Search,
  RefreshCw,
  Copy,
  Check,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Zap,
  Hash,
} from "lucide-react";
import { useTrends, useDiscoverTrends, type Trend } from "../hooks/useTrends";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";

function RelevanceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70
      ? "bg-success"
      : pct >= 40
        ? "bg-warning"
        : "bg-text-tertiary";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-border-subtle">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-caption text-text-tertiary">{pct}%</span>
    </div>
  );
}

function VolumeChange({ pct }: { pct: number }) {
  if (pct > 5)
    return (
      <span className="inline-flex items-center gap-0.5 text-caption text-success">
        <ArrowUpRight className="h-3 w-3" />+{pct.toFixed(0)}%
      </span>
    );
  if (pct < -5)
    return (
      <span className="inline-flex items-center gap-0.5 text-caption text-danger">
        <ArrowDownRight className="h-3 w-3" />{pct.toFixed(0)}%
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 text-caption text-text-tertiary">
      <Minus className="h-3 w-3" />{pct.toFixed(0)}%
    </span>
  );
}

function TrendCard({ trend, index }: { trend: Trend; index: number }) {
  const [copied, setCopied] = useState<string | null>(null);

  function copyText(text: string, label: string) {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  }

  const sourceLabel =
    trend.source === "google_trends"
      ? "Google"
      : trend.source === "x_twitter"
        ? "X"
        : "Combined";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.2 }}
    >
      <Card className="p-lg space-y-lg hover:-translate-y-0.5 hover:shadow-md transition-all">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-body-medium text-text-primary">
                {trend.keyword}
              </h3>
              <Badge variant={trend.relevance_score >= 0.7 ? "approved" : "default"} dot>
                {sourceLabel}
              </Badge>
            </div>
            <div className="mt-1 flex items-center gap-3">
              <span className="text-caption text-text-tertiary">
                Vol: {trend.volume}
              </span>
              <VolumeChange pct={trend.volume_change_pct} />
              {trend.sentiment_score !== null && (
                <span className="text-caption text-text-tertiary">
                  Sentiment: {(trend.sentiment_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="text-caption text-text-tertiary">Relevance</p>
            <RelevanceBar score={trend.relevance_score} />
          </div>
        </div>

        {/* AI Suggestion */}
        {trend.ai_suggestion && (
          <div className="rounded-lg bg-accent-subtle p-md">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Sparkles className="h-3.5 w-3.5 text-accent" strokeWidth={1.5} />
              <span className="text-caption font-medium text-accent">AI Suggestion</span>
            </div>
            <p className="text-body text-text-primary">{trend.ai_suggestion}</p>
          </div>
        )}

        {/* Caption draft */}
        {trend.ai_caption_draft && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-caption font-medium text-text-secondary">
                Draft Caption
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyText(trend.ai_caption_draft!, "caption")}
              >
                {copied === "caption" ? (
                  <Check className="h-3.5 w-3.5 text-success" />
                ) : (
                  <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
                )}
              </Button>
            </div>
            <p className="text-body text-text-secondary italic">
              "{trend.ai_caption_draft}"
            </p>
          </div>
        )}

        {/* Hashtags */}
        {trend.ai_hashtags && trend.ai_hashtags.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-caption font-medium text-text-secondary">
                <Hash className="inline h-3 w-3" strokeWidth={1.5} /> Hashtags
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  copyText(trend.ai_hashtags!.join(" "), "hashtags")
                }
              >
                {copied === "hashtags" ? (
                  <Check className="h-3.5 w-3.5 text-success" />
                ) : (
                  <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
                )}
              </Button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {trend.ai_hashtags.map((tag, i) => (
                <Badge key={i} variant="default">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

export default function TrendsPage() {
  const { data: trends, isLoading, refetch } = useTrends();
  const discover = useDiscoverTrends();

  const [showForm, setShowForm] = useState(false);
  const [keywords, setKeywords] = useState("");
  const [niche, setNiche] = useState("marketing and creative content");
  const [region, setRegion] = useState("US");

  function handleDiscover(e: FormEvent) {
    e.preventDefault();
    discover.mutate({
      keywords: keywords
        ? keywords.split(",").map((k) => k.trim()).filter(Boolean)
        : undefined,
      region,
      niche,
    });
    setShowForm(false);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-display text-text-primary">Trends</h1>
          {trends && <Badge>{trends.length} active</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className="h-4 w-4" strokeWidth={1.5} />
            Refresh
          </Button>
          <Button onClick={() => setShowForm(!showForm)}>
            <Zap className="h-4 w-4" strokeWidth={1.5} />
            Discover
          </Button>
        </div>
      </div>

      <p className="mt-2 text-body text-text-secondary">
        AI-powered trend intelligence from Google Trends and X. Get content
        suggestions before your competitors do.
      </p>

      {/* Discover form */}
      <AnimatePresence>
        {showForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleDiscover}
            className="mt-lg overflow-hidden rounded-lg border border-border bg-surface p-lg space-y-lg"
          >
            <div className="grid grid-cols-1 gap-lg sm:grid-cols-3">
              <Input
                label="Keywords (optional)"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="e.g. AI, marketing, brand"
              />
              <Input
                label="Your Niche"
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                placeholder="e.g. fashion marketing"
              />
              <Input
                label="Region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="US, BR, GB..."
              />
            </div>
            <Button type="submit" loading={discover.isPending}>
              <Search className="h-4 w-4" strokeWidth={1.5} />
              Discover Trends
            </Button>
            {discover.isPending && (
              <p className="text-caption text-text-tertiary">
                Fetching from Google Trends + X, then analyzing with Claude AI...
                this may take 15-30 seconds.
              </p>
            )}
          </motion.form>
        )}
      </AnimatePresence>

      {/* Trend list */}
      {isLoading ? (
        <div className="mt-xl space-y-lg">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-48 animate-pulse rounded-lg bg-border-subtle"
            />
          ))}
        </div>
      ) : trends && trends.length > 0 ? (
        <div className="mt-xl space-y-lg">
          {trends.map((trend, i) => (
            <TrendCard key={trend.id} trend={trend} index={i} />
          ))}
        </div>
      ) : (
        <div className="mt-3xl flex flex-col items-center gap-3 text-center">
          <TrendingUp
            className="h-12 w-12 text-text-tertiary"
            strokeWidth={1}
          />
          <p className="text-body text-text-secondary">No trends discovered yet</p>
          <p className="text-caption text-text-tertiary">
            Click "Discover" to fetch trending topics and get AI-powered content
            suggestions.
          </p>
          <Button onClick={() => setShowForm(true)}>
            <Zap className="h-4 w-4" strokeWidth={1.5} />
            Discover Trends
          </Button>
        </div>
      )}
    </div>
  );
}
