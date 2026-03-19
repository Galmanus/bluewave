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
} from "lucide-react";
import { useWallet } from "../hooks/useWallet";

const WAVE_API = import.meta.env.VITE_WAVE_API_URL || `http://${window.location.hostname}:8300/api/v1/wave`;

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
        "I'm Wave. I own and operate Bluewave. 9 specialist agents work under me. I check brand compliance, manage creative assets, and guard your brand DNA. Upload an image and I'll tell you if it's on-brand. What do you need?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => `web_${crypto.randomUUID()}`);
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
    { label: "Pesquisar web", icon: Search, prompt: "Search the web for latest AI agent news" },
    { label: "Prospectar clientes", icon: Globe, prompt: "Find creative agencies that need content operations help" },
    { label: "Status Hedera", icon: Zap, prompt: "Show me the Hedera platform stats and cost comparison" },
    { label: "Skills do Wave", icon: Brain, prompt: "List all your skills and capabilities" },
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
            <h1 className="text-heading text-text-primary">Wave Agent</h1>
            <p className="text-caption text-text-tertiary">
              76 tools &middot; 9 specialists &middot; PUT framework &middot; self-evolving
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
              <p className="whitespace-pre-wrap">{msg.content}</p>
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
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Fale com o Wave..."
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
