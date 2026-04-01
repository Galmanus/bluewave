import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Upload, Dna, Loader2, Check, Copy } from "lucide-react";
import { useGeo } from "../contexts/GeoContext";
import { toast } from "sonner";

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || "/api/v1/wave";

export default function BrandDNAPage() {
  const { geo } = useGeo();
  const p = geo.lang === "pt";

  const [brandName, setBrandName] = useState("");
  const [textContent, setTextContent] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const handleImageUpload = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      setImagePreview(dataUrl);
      setImageB64(dataUrl.split(",")[1]);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleExtract = async () => {
    if (!brandName && !textContent && !imageB64) {
      toast.error(p ? "Forneça pelo menos um input" : "Provide at least one input");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${WAVE_API}/brand/extract-dna`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: brandName,
          text_content: textContent || undefined,
          image_base64: imageB64 || undefined,
          media_type: "image/jpeg",
        }),
      });
      const data = await res.json();
      setResult(data);
      if (data.success) {
        toast.success(p ? "Brand DNA extraído com sucesso!" : "Brand DNA extracted!");
      } else {
        toast.error(data.error || "Extraction failed");
      }
    } catch {
      toast.error(p ? "Erro ao conectar com o servidor" : "Connection error");
    }

    setLoading(false);
  };

  const copyJSON = () => {
    if (result?.brand_dna) {
      navigator.clipboard.writeText(JSON.stringify(result.brand_dna, null, 2));
      toast.success(p ? "JSON copiado!" : "JSON copied!");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-xl">
      <div>
        <h1 className="text-heading text-text-primary">
          {p ? "Extração de Brand DNA" : "Brand DNA Extraction"}
        </h1>
        <p className="text-body text-text-secondary mt-1">
          {p
            ? "Extraia a identidade completa da marca a partir de guidelines, imagens ou descrições. O resultado é um JSON estruturado usado em todos os checks de compliance."
            : "Extract complete brand identity from guidelines, images, or descriptions. The result is a structured JSON used for all compliance checks."}
        </p>
      </div>

      {/* Inputs */}
      <div className="grid gap-lg md:grid-cols-2">
        {/* Brand name + text */}
        <div className="space-y-lg">
          <div>
            <label className="block text-body-medium text-text-primary mb-1">
              {p ? "Nome da marca" : "Brand name"}
            </label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              placeholder={p ? "Ex: Ferpa Design" : "e.g., Acme Corp"}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-body text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-body-medium text-text-primary mb-1">
              {p ? "Descrição / Guidelines (texto)" : "Description / Guidelines (text)"}
            </label>
            <textarea
              rows={6}
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder={p
                ? "Cole aqui o texto das brand guidelines, tom de voz, cores, regras..."
                : "Paste brand guidelines text, tone of voice, colors, rules..."}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-body text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none resize-none"
            />
          </div>
        </div>

        {/* Image upload */}
        <div>
          <label className="block text-body-medium text-text-primary mb-1">
            {p ? "Imagem da guideline (opcional)" : "Guideline image (optional)"}
          </label>
          <div
            className="relative border-2 border-dashed border-border rounded-xl p-6 text-center hover:border-accent/50 transition-colors cursor-pointer min-h-[200px] flex items-center justify-center"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) handleImageUpload(file);
            }}
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = "image/*";
              input.onchange = (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (file) handleImageUpload(file);
              };
              input.click();
            }}
          >
            {imagePreview ? (
              <img src={imagePreview} alt="Preview" className="max-h-[250px] rounded-lg object-contain" />
            ) : (
              <div className="text-text-tertiary space-y-2">
                <Upload className="h-8 w-8 mx-auto" strokeWidth={1} />
                <p className="text-body">{p ? "Arraste ou clique para enviar" : "Drag or click to upload"}</p>
                <p className="text-caption">{p ? "Página do manual de marca, logo, paleta..." : "Brand manual page, logo, palette..."}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Extract button */}
      <motion.button
        whileTap={{ scale: 0.98 }}
        onClick={handleExtract}
        disabled={loading || (!brandName && !textContent && !imageB64)}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-accent text-white font-semibold text-lg hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            {p ? "Extraindo Brand DNA..." : "Extracting Brand DNA..."}
          </>
        ) : (
          <>
            <Dna className="h-5 w-5" />
            {p ? "Extrair Brand DNA" : "Extract Brand DNA"}
          </>
        )}
      </motion.button>

      {/* Result */}
      {result?.success && result.brand_dna && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-success/20 bg-success/5 p-lg space-y-md"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-success">
              <Check className="h-5 w-5" />
              <span className="text-body-medium">
                {p ? "Brand DNA extraído com sucesso" : "Brand DNA extracted successfully"}
              </span>
            </div>
            <button
              onClick={copyJSON}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-caption text-text-secondary hover:bg-surface-raised transition-colors"
            >
              <Copy className="h-3.5 w-3.5" />
              {p ? "Copiar JSON" : "Copy JSON"}
            </button>
          </div>

          {/* Key info */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {result.brand_dna.brand_name && (
              <div className="rounded-lg bg-surface p-3">
                <p className="text-caption text-text-tertiary">{p ? "Marca" : "Brand"}</p>
                <p className="text-body-medium text-text-primary">{result.brand_dna.brand_name}</p>
              </div>
            )}
            {result.brand_dna.primary_colors && (
              <div className="rounded-lg bg-surface p-3">
                <p className="text-caption text-text-tertiary">{p ? "Cores primárias" : "Primary colors"}</p>
                <div className="flex gap-1 mt-1">
                  {result.brand_dna.primary_colors.slice(0, 5).map((c: string) => (
                    <div key={c} className="w-5 h-5 rounded-full border border-border" style={{ background: c }} title={c} />
                  ))}
                </div>
              </div>
            )}
            {result.brand_dna.fonts?.primary && (
              <div className="rounded-lg bg-surface p-3">
                <p className="text-caption text-text-tertiary">{p ? "Fonte" : "Font"}</p>
                <p className="text-body-medium text-text-primary">{result.brand_dna.fonts.primary}</p>
              </div>
            )}
            {result.brand_dna.tone_adjectives && (
              <div className="rounded-lg bg-surface p-3">
                <p className="text-caption text-text-tertiary">{p ? "Tom" : "Tone"}</p>
                <p className="text-body-medium text-text-primary">{result.brand_dna.tone_adjectives.slice(0, 3).join(", ")}</p>
              </div>
            )}
          </div>

          {/* Full JSON */}
          <details>
            <summary className="text-caption text-text-secondary cursor-pointer hover:text-text-primary">
              {p ? "Ver JSON completo" : "View full JSON"}
            </summary>
            <pre className="mt-2 p-3 rounded-lg bg-[#0d1117] text-[11px] text-green-400/80 overflow-auto max-h-[400px] font-mono">
              {JSON.stringify(result.brand_dna, null, 2)}
            </pre>
          </details>

          {result.tokens_used && (
            <p className="text-caption text-text-tertiary">
              Tokens: {result.tokens_used.input} in / {result.tokens_used.output} out
              {result.elapsed_seconds && ` · ${result.elapsed_seconds}s`}
            </p>
          )}
        </motion.div>
      )}

      {result && !result.success && (
        <div className="rounded-xl border border-danger/20 bg-danger-subtle p-md text-body text-danger">
          {result.error || "Extraction failed"}
        </div>
      )}
    </div>
  );
}
