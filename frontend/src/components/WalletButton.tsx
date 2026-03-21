import { Wallet, LogOut, ExternalLink, AlertCircle } from "lucide-react";
import { useWallet } from "../hooks/useWallet";
import { useGeo } from "../contexts/GeoContext";

export default function WalletButton() {
  const { geo } = useGeo();

  // Crypto wallet not available in Brazil (regulatory compliance)
  if (geo.isBrazil) return null;
  const {
    address,
    balance,
    shortAddress,
    hasMetaMask,
    isConnecting,
    isCorrectNetwork,
    error,
    connect,
    disconnect,
    switchToHedera,
  } = useWallet();

  if (!hasMetaMask) {
    return (
      <a
        href="https://metamask.io/download/"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-caption text-text-secondary hover:bg-accent-subtle transition-colors"
      >
        <Wallet className="h-3.5 w-3.5" />
        Install MetaMask
      </a>
    );
  }

  if (!address) {
    return (
      <button
        onClick={connect}
        disabled={isConnecting}
        className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-3 py-1.5 text-caption font-medium text-white hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50"
      >
        <Wallet className="h-3.5 w-3.5" />
        {isConnecting ? "Connecting..." : "Connect Wallet"}
      </button>
    );
  }

  if (!isCorrectNetwork) {
    return (
      <button
        onClick={switchToHedera}
        className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-caption font-medium text-amber-400 hover:bg-amber-500/20 transition-colors"
      >
        <AlertCircle className="h-3.5 w-3.5" />
        Switch to Hedera
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5">
        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-caption font-mono text-text-primary">{shortAddress}</span>
        <span className="text-caption text-text-tertiary">
          {balance ? `${parseFloat(balance).toFixed(2)} HBAR` : "..."}
        </span>
      </div>
      <button
        onClick={disconnect}
        className="rounded-md p-1.5 text-text-tertiary hover:text-danger transition-colors"
        title="Disconnect wallet"
      >
        <LogOut className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
