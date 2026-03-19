import { FormEvent, useEffect, useState } from "react";
import { Palette, Plus, Trash2, Save, ShieldCheck } from "lucide-react";
import {
  useBrandGuidelines,
  useUpdateBrandGuidelines,
} from "../hooks/useBrand";
import { Button } from "../components/ui/Button";
import { Textarea } from "../components/ui/Input";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

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
    if (/^#[0-9a-fA-F]{3,8}$/.test(draft) && !colors.includes(draft)) {
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
    </div>
  );
}
