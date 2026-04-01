import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Send,
  Bot,
  User,
  Loader2,
  Sparkles,
  Brain,
  Search,
  Globe,
  Zap,
  RotateCcw,
  Wallet,
  ExternalLink,
  CheckCircle2,
  Upload,
} from "lucide-react";
import { useWallet } from "../hooks/useWallet";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || "/api/v1/wave";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  txHash?: string;
  txUrl?: string;
}

export default function WaveAgentPage() {
  const wallet = useWallet();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Bluewave Guardian. Upload an image and I analyze it against your Brand DNA across 8 dimensions: colors, typography, logo, tone, composition, photography, strategic coherence, and channel fit. Score 0-100 with specific fixes. Drop an image to start.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => `web_${Date.now()}_${Math.random().toString(36).slice(2)}`);
  const [totalSpent, setTotalSpent] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      // Try SSE streaming first, fall back to regular POST
      try {
        const res = await fetch(`${WAVE_API}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!res.ok || !res.body) throw new Error("Stream unavailable");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = "";
        const msgId = `assistant_${Date.now()}`;

        // Add placeholder message
        setMessages((prev) => [
          ...prev,
          { id: msgId, role: "assistant", content: "", timestamp: new Date() },
        ]);

        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "chunk") {
                fullResponse += event.text;
                setMessages((prev) =>
                  prev.map((m) => (m.id === msgId ? { ...m, content: fullResponse } : m))
                );
              } else if (event.type === "done") {
                fullResponse = event.response;
                setMessages((prev) =>
                  prev.map((m) => (m.id === msgId ? { ...m, content: fullResponse } : m))
                );
              } else if (event.type === "error") {
                throw new Error(event.message);
              }
            } catch { /* ignore parse errors for incomplete chunks */ }
          }
        }

        return { response: fullResponse };
      } catch {
        // Fallback to regular POST
        const res = await fetch(`${WAVE_API}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
        });
        if (!res.ok) throw new Error("Wave unavailable");
        return res.json();
      }
    },
    onSuccess: async (data) => {
      // Only add message if we used the non-streaming fallback (no placeholder yet)
      setMessages((prev) => {
        const hasPlaceholder = prev.some((m) => m.role === "assistant" && m.content === data.response);
        if (hasPlaceholder) return prev;
        return [
          ...prev,
          { id: `assistant_${Date.now()}`, role: "assistant", content: data.response, timestamp: new Date() },
        ];
      });

      // If wallet is connected, charge for the AI action on Hedera
      if (wallet.address) {
        try {
          const tx = await wallet.payForAction("ai_chat");
          setTotalSpent((prev) => prev + 0.05);
          setMessages((prev) => [
            ...prev,
            {
              id: `tx_${Date.now()}`,
              role: "system",
              content: `Paid 0.33 HBAR (~$0.05) for this action`,
              timestamp: new Date(),
              txHash: tx.txHash,
              txUrl: tx.explorerUrl,
            },
          ]);
        } catch {
          // Payment failed silently — don't block the UX
        }
      }
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: `error_${Date.now()}`,
          role: "assistant",
          content: "Estou offline no momento. Tenta de novo em breve.",
          timestamp: new Date(),
        },
      ]);
    },
  });

  const handleSend = () => {
    const text = input.trim();
    if (!text || chatMutation.isPending) return;

    setMessages((prev) => [
      ...prev,
      {
        id: `user_${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      },
    ]);
    setInput("");
    chatMutation.mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = async () => {
    await fetch(`${WAVE_API}/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {});
    setMessages([
      {
        id: "reset",
        role: "assistant",
        content: "Contexto limpo. Nova conversa.",
        timestamp: new Date(),
      },
    ]);
  };

  const QUICK_ACTIONS = [
    { label: "Ver Brand DNA", icon: Brain, prompt: "Mostre o Brand DNA cadastrado com cores, fontes, tom e regras" },
    { label: "Como funciona", icon: Search, prompt: "Explique as 8 dimensoes de analise de brand compliance" },
    { label: "Enviar imagem", icon: Globe, prompt: "Quero analisar uma imagem contra o Brand DNA" },
    { label: "Regras da marca", icon: Zap, prompt: "Liste todos os dos e donts da marca cadastrada" },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400">
            <Bot className="h-5 w-5 text-white" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-heading text-text-primary">Brand Guardian</h1>
            <p className="text-caption text-text-tertiary">
              8 dimensions &middot; Delta-E color science &middot; WCAG accessibility &middot; AI Vision
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {wallet.address ? (
            <div className="flex items-center gap-2 rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-1.5">
              <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-[11px] font-mono text-text-primary">{wallet.shortAddress}</span>
              <span className="text-[10px] text-text-tertiary">
                {wallet.balance ? `${parseFloat(wallet.balance).toFixed(1)} HBAR` : ""}
              </span>
              {totalSpent > 0 && (
                <span className="text-[10px] text-amber-400 ml-1">
                  -${totalSpent.toFixed(2)}
                </span>
              )}
            </div>
          ) : (
            <button
              onClick={wallet.connect}
              className="flex items-center gap-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-[11px] font-medium text-purple-400 hover:bg-purple-500/20 transition-colors"
            >
              <Wallet className="h-3 w-3" />
              Connect to pay with HBAR
            </button>
          )}
          <button
            onClick={handleReset}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-caption text-text-secondary hover:bg-accent-subtle transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto py-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""} ${msg.role === "system" ? "justify-center" : ""}`}
          >
            {msg.role === "system" && (
              <div className="flex items-center gap-2 rounded-full bg-green-500/10 border border-green-500/20 px-3 py-1.5">
                <CheckCircle2 className="h-3 w-3 text-green-400" />
                <span className="text-[11px] text-green-400">{msg.content}</span>
                {msg.txUrl && (
                  <a
                    href={msg.txUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[10px] text-green-300 hover:text-green-200 transition-colors"
                  >
                    <ExternalLink className="h-2.5 w-2.5" />
                    verify
                  </a>
                )}
              </div>
            )}
            {msg.role === "assistant" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/10 to-cyan-400/10 border border-blue-500/20">
                <Sparkles className="h-4 w-4 text-blue-500" />
              </div>
            )}
            {msg.role !== "system" && (
            <div
              className={`max-w-[75%] rounded-xl px-4 py-3 text-body ${
                msg.role === "user"
                  ? "bg-accent text-white"
                  : "bg-surface-raised border border-border"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm prose-invert max-w-none [&_table]:text-xs [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-surface [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm [&_h2]:mt-4 [&_h3]:mt-3 [&_p]:text-sm [&_li]:text-sm [&_hr]:border-border [&_hr]:my-3 [&_strong]:text-text-primary [&_code]:text-accent [&_code]:bg-surface [&_code]:px-1 [&_code]:rounded">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
              <p
                className={`mt-1 text-[10px] ${
                  msg.role === "user"
                    ? "text-white/50"
                    : "text-text-tertiary"
                }`}
              >
                {msg.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
            )}
            {msg.role === "user" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/10 border border-accent/20">
                <User className="h-4 w-4 text-accent" />
              </div>
            )}
          </div>
        ))}

        {chatMutation.isPending && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/10 to-cyan-400/10 border border-blue-500/20">
              <Sparkles className="h-4 w-4 text-blue-500" />
            </div>
            <div className="rounded-xl bg-surface-raised border border-border px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-text-tertiary" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 pb-3">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => {
                setInput(action.prompt);
                setTimeout(() => {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `user_${Date.now()}`,
                      role: "user",
                      content: action.prompt,
                      timestamp: new Date(),
                    },
                  ]);
                  setInput("");
                  chatMutation.mutate(action.prompt);
                }, 100);
              }}
              className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-caption text-text-secondary hover:bg-accent-subtle hover:text-text-primary hover:border-accent/30 transition-colors"
            >
              <action.icon className="h-3.5 w-3.5" />
              {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border pt-3">
        <div className="flex gap-2">
          <button
            onClick={() => {
              const inp = document.createElement("input");
              inp.type = "file";
              inp.accept = "image/*";
              inp.onchange = async (e: Event) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (!file) return;

                // Compress image client-side before sending (max 2MB, 1600px)
                const compressImage = (file: File): Promise<string> => {
                  return new Promise((resolve) => {
                    const img = new Image();
                    img.onload = () => {
                      const canvas = document.createElement("canvas");
                      const MAX = 1600;
                      let w = img.width, h = img.height;
                      if (w > MAX || h > MAX) {
                        if (w > h) { h = Math.round(h * MAX / w); w = MAX; }
                        else { w = Math.round(w * MAX / h); h = MAX; }
                      }
                      canvas.width = w;
                      canvas.height = h;
                      canvas.getContext("2d")!.drawImage(img, 0, 0, w, h);
                      resolve(canvas.toDataURL("image/jpeg", 0.8).split(",")[1]);
                    };
                    img.src = URL.createObjectURL(file);
                  });
                };

                const base64Data = await compressImage(file);
                const mediaType = "image/jpeg";

                // Show upload message
                const msgId = `analysis_${Date.now()}`;
                setMessages((prev) => [
                  ...prev,
                  { id: `user_img_${Date.now()}`, role: "user", content: `[${file.name}]`, timestamp: new Date() },
                  { id: msgId, role: "assistant", content: "Analyzing against Brand DNA...", timestamp: new Date() },
                ]);

                try {
                  const res = await fetch(`${WAVE_API}/compliance-check`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ image_base64: base64Data, media_type: mediaType }),
                  });
                  const data = await res.json();
                  setMessages((prev) =>
                    prev.map((m) => m.id === msgId ? { ...m, content: data.response || "No result." } : m)
                  );
                } catch (err) {
                  setMessages((prev) =>
                    prev.map((m) => m.id === msgId ? { ...m, content: "Analysis failed. Guardian may be offline." } : m)
                  );
                }
              };
              inp.click();
            }}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-text-secondary hover:bg-accent-subtle hover:text-accent hover:border-accent/30 transition-colors"
            title="Upload image for compliance check"
          >
            <Upload className="h-5 w-5" />
          </button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Upload an image or ask about your Brand DNA..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-border bg-surface px-4 py-3 text-body text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || chatMutation.isPending}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent text-white hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {chatMutation.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
