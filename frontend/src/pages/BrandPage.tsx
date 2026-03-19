import { FormEvent, useEffect, useState, useCallback } from "react";
import { Palette, Plus, Trash2, Save, ShieldCheck, Upload, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import {
  useBrandGuidelines,
  useUpdateBrandGuidelines,
} from "../hooks/useBrand";
import { Button } from "../components/ui/Button";
import { Textarea } from "../components/ui/Input";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || `http://${window.location.hostname}:8300/api/v1/wave`;

function ListEditor({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  function add() {
    const val = draft.trim();
    if (val && !items.includes(val)) {
      onChange([...items, val]);
      setDraft("");
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-body-medium text-text-primary">{label}</label>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={placeholder}
          className="flex-1 h-10 rounded-md border border-border bg-surface px-3 text-body text-text-primary focus-ring"
        />
        <Button type="button" variant="secondary" size="sm" onClick={add}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 rounded-full bg-accent-subtle px-2.5 py-1 text-caption text-accent"
          >
            {item}
            <button
              type="button"
              onClick={() => onChange(items.filter((_, j) => j !== i))}
              className="hover:text-danger"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

function ColorEditor({
  label,
  colors,
  onChange,
}: {
  label: string;
  colors: string[];
  onChange: (colors: string[]) => void;
}) {
  const [draft, setDraft] = useState("#");

  function add() {
    if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(draft) && !colors.includes(draft)) {
      onChange([...colors, draft]);
      setDraft("#");
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-body-medium text-text-primary">{label}</label>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder="#2563EB"
          className="w-32 h-10 rounded-md border border-border bg-surface px-3 text-body text-text-primary font-mono focus-ring"
        />
        <Button type="button" variant="secondary" size="sm" onClick={add}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {colors.map((color, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onChange(colors.filter((_, j) => j !== i))}
            className="group relative h-8 w-8 rounded-md border border-border shadow-xs hover:ring-2 hover:ring-danger"
            style={{ backgroundColor: color }}
            title={`${color} — click to remove`}
          >
            <Trash2 className="absolute inset-0 m-auto h-3 w-3 text-white opacity-0 group-hover:opacity-100 drop-shadow" />
          </button>
        ))}
      </div>
    </div>
  );
}

export default function BrandPage() {
  const { data: guidelines, isLoading } = useBrandGuidelines();
  const update = useUpdateBrandGuidelines();

  const [primaryColors, setPrimaryColors] = useState<string[]>([]);
  const [secondaryColors, setSecondaryColors] = useState<string[]>([]);
  const [fonts, setFonts] = useState<string[]>([]);
  const [tone, setTone] = useState("");
  const [dos, setDos] = useState<string[]>([]);
  const [donts, setDonts] = useState<string[]>([]);

  useEffect(() => {
    if (guidelines) {
      setPrimaryColors(guidelines.primary_colors || []);
      setSecondaryColors(guidelines.secondary_colors || []);
      setFonts(guidelines.fonts || []);
      setTone(guidelines.tone_description || "");
      setDos(guidelines.dos || []);
      setDonts(guidelines.donts || []);
    }
  }, [guidelines]);

  function handleSave(e: FormEvent) {
    e.preventDefault();
    update.mutate({
      primary_colors: primaryColors,
      secondary_colors: secondaryColors,
      fonts,
      tone_description: tone,
      dos,
      donts,
    });
  }

  if (isLoading) {
    return (
      <div className="space-y-lg">
        <div className="h-8 w-48 animate-pulse rounded bg-border-subtle" />
        <div className="h-64 animate-pulse rounded-lg bg-border-subtle" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <h1 className="text-display text-text-primary">Brand Guidelines</h1>
        <Badge variant={guidelines ? "approved" : "draft"} dot>
          {guidelines ? "Active" : "Not configured"}
        </Badge>
      </div>
      <p className="mt-2 text-body text-text-secondary">
        Define your brand rules. The AI agent will check every asset against
        these guidelines before approval.
      </p>

      <form onSubmit={handleSave} className="mt-xl space-y-xl">
        {/* Colors */}
        <Card className="p-lg space-y-lg">
          <h2 className="text-heading text-text-primary flex items-center gap-2">
            <Palette className="h-5 w-5 text-accent" strokeWidth={1.5} />
            Colors
          </h2>
          <div className="grid grid-cols-1 gap-lg sm:grid-cols-2">
            <ColorEditor
              label="Primary Colors"
              colors={primaryColors}
              onChange={setPrimaryColors}
            />
            <ColorEditor
              label="Secondary Colors"
              colors={secondaryColors}
              onChange={setSecondaryColors}
            />
          </div>
        </Card>

        {/* Typography */}
        <Card className="p-lg space-y-lg">
          <h2 className="text-heading text-text-primary">Typography</h2>
          <ListEditor
            label="Approved Fonts"
            items={fonts}
            onChange={setFonts}
            placeholder="e.g. Inter, Helvetica"
          />
        </Card>

        {/* Tone */}
        <Card className="p-lg space-y-lg">
          <h2 className="text-heading text-text-primary">Brand Voice & Tone</h2>
          <Textarea
            label="Tone Description"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            placeholder="e.g. Professional but approachable. Use active voice. Avoid jargon. Be concise."
            rows={3}
          />
        </Card>

        {/* Do's and Don'ts */}
        <div className="grid grid-cols-1 gap-lg sm:grid-cols-2">
          <Card className="p-lg space-y-lg">
            <h2 className="text-heading text-success flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" strokeWidth={1.5} />
              Do's
            </h2>
            <ListEditor
              label="Brand rules to follow"
              items={dos}
              onChange={setDos}
              placeholder="e.g. Always include the tagline"
            />
          </Card>
          <Card className="p-lg space-y-lg">
            <h2 className="text-heading text-danger flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" strokeWidth={1.5} />
              Don'ts
            </h2>
            <ListEditor
              label="Rules to avoid"
              items={donts}
              onChange={setDonts}
              placeholder="e.g. Never use the old logo"
            />
          </Card>
        </div>

        <Button type="submit" loading={update.isPending}>
          <Save className="h-4 w-4" strokeWidth={1.5} />
          Save Guidelines
        </Button>
      </form>

      {/* Compliance Check Section */}
      {guidelines && (
        <ComplianceChecker brandName={guidelines.custom_rules?.brand_name || "your brand"} />
      )}
    </div>
  );
}

function ComplianceChecker({ brandName }: { brandName: string }) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) return;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);

    // Send to Wave for compliance check
    setChecking(true);
    setResult(null);
    try {
      const base64 = await new Promise<string>((resolve) => {
        const r = new FileReader();
        r.onload = () => resolve((r.result as string).split(",")[1]);
        r.readAsDataURL(file);
      });

      const res = await fetch(`${WAVE_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Analyze this image for brand compliance. Check colors, typography, tone, and all brand rules. Return a score 0-100 and specific issues.\n<brand_name>${brandName.replace(/[<>]/g, "")}</brand_name>\n<image_data>${base64.substring(0, 500)}</image_data>`,
          session_id: "compliance_check_" + Date.now(),
        }),
      });
      const data = await res.json();
      setResult({ success: true, analysis: data.response });
    } catch (err) {
      setResult({ success: false, analysis: "Failed to analyze. Wave may be offline." });
    }
    setChecking(false);
  }, [brandName]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <Card className="mt-xl p-lg space-y-lg">
      <h2 className="text-heading text-text-primary flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-accent" strokeWidth={1.5} />
        Brand Compliance Check
      </h2>
      <p className="text-body text-text-secondary">
        Drop an image to check if it follows {brandName}'s brand guidelines.
        Wave analyzes colors, typography, composition and tone against your Brand DNA.
      </p>

      {/* Drop zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        className={`relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 transition-colors cursor-pointer ${
          dragOver
            ? "border-accent bg-accent-subtle/30"
            : "border-border-subtle hover:border-accent/50"
        }`}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = "image/*";
          input.onchange = (e: any) => {
            const file = e.target.files[0];
            if (file) handleFile(file);
          };
          input.click();
        }}
      >
        {preview ? (
          <img src={preview} alt="Preview" className="max-h-48 rounded-lg" />
        ) : (
          <>
            <Upload className="h-10 w-10 text-text-tertiary" strokeWidth={1} />
            <span className="text-body text-text-secondary">
              Drop an image here or click to upload
            </span>
          </>
        )}
        {checking && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface/80 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              <span className="text-body-medium text-accent">Wave is analyzing...</span>
            </div>
          </div>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className={`rounded-xl p-lg ${
          result.success ? "bg-surface-raised" : "bg-danger-subtle"
        }`}>
          <div className="prose prose-sm max-w-none text-text-primary whitespace-pre-wrap">
            {result.analysis}
          </div>
        </div>
      )}
    </Card>
  );
}
