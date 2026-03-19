import { useState, useCallback, useEffect } from "react";
import { BrowserProvider, formatEther, parseEther } from "ethers";

// Hedera EVM network config
const HEDERA_NETWORKS = {
  testnet: {
    chainId: "0x128", // 296
    chainName: "Hedera Testnet",
    rpcUrls: ["https://testnet.hashio.io/api"],
    nativeCurrency: { name: "HBAR", symbol: "HBAR", decimals: 18 },
    blockExplorerUrls: ["https://hashscan.io/testnet"],
  },
  mainnet: {
    chainId: "0x127", // 295
    chainName: "Hedera Mainnet",
    rpcUrls: ["https://mainnet.hashio.io/api"],
    nativeCurrency: { name: "HBAR", symbol: "HBAR", decimals: 18 },
    blockExplorerUrls: ["https://hashscan.io/mainnet"],
  },
};

const NETWORK = HEDERA_NETWORKS.mainnet;
const AI_ACTION_COST_HBAR = "0.33"; // ~$0.05 at $0.15/HBAR

// Manuel's wallet — all payments go here
const TREASURY_ADDRESS = import.meta.env.VITE_TREASURY_ADDRESS || "0x46eb000000000000000000000000000000002381";

interface WalletState {
  address: string | null;
  balance: string | null;
  chainId: number | null;
  isConnecting: boolean;
  isCorrectNetwork: boolean;
  error: string | null;
}

export function useWallet() {
  const [state, setState] = useState<WalletState>({
    address: null,
    balance: null,
    chainId: null,
    isConnecting: false,
    isCorrectNetwork: false,
    error: null,
  });

  const hasMetaMask = typeof window !== "undefined" && !!(window as any).ethereum;

  const getProvider = useCallback(() => {
    if (!hasMetaMask) return null;
    return new BrowserProvider((window as any).ethereum);
  }, [hasMetaMask]);

  const updateBalance = useCallback(async (address: string) => {
    const provider = getProvider();
    if (!provider) return;
    try {
      const balance = await provider.getBalance(address);
      setState((prev) => ({ ...prev, balance: formatEther(balance) }));
    } catch {
      // ignore
    }
  }, [getProvider]);

  const switchToHedera = useCallback(async () => {
    if (!hasMetaMask) return;
    const ethereum = (window as any).ethereum;

    try {
      await ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: NETWORK.chainId }],
      });
    } catch (switchError: any) {
      // Chain not added yet — add it
      if (switchError.code === 4902) {
        await ethereum.request({
          method: "wallet_addEthereumChain",
          params: [NETWORK],
        });
      }
    }
  }, [hasMetaMask]);

  const connect = useCallback(async () => {
    if (!hasMetaMask) {
      setState((prev) => ({ ...prev, error: "Install MetaMask to connect" }));
      return;
    }

    setState((prev) => ({ ...prev, isConnecting: true, error: null }));

    try {
      const provider = getProvider()!;
      const accounts = await provider.send("eth_requestAccounts", []);
      const address = accounts[0];
      const network = await provider.getNetwork();
      const chainId = Number(network.chainId);
      const isCorrect = chainId === 296 || chainId === 295;

      if (!isCorrect) {
        await switchToHedera();
      }

      const balance = await provider.getBalance(address);

      setState({
        address,
        balance: formatEther(balance),
        chainId,
        isConnecting: false,
        isCorrectNetwork: true,
        error: null,
      });
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: err.message?.slice(0, 100) || "Connection failed",
      }));
    }
  }, [hasMetaMask, getProvider, switchToHedera]);

  const disconnect = useCallback(() => {
    setState({
      address: null,
      balance: null,
      chainId: null,
      isConnecting: false,
      isCorrectNetwork: false,
      error: null,
    });
  }, []);

  const payForAction = useCallback(
    async (actionType: string, recipientAddress?: string) => {
      if (!state.address) throw new Error("Wallet not connected");

      const provider = getProvider()!;
      const signer = await provider.getSigner();

      const tx = await signer.sendTransaction({
        to: recipientAddress || TREASURY_ADDRESS,
        value: parseEther(AI_ACTION_COST_HBAR),
        data: new TextEncoder().encode(JSON.stringify({
          type: "bluewave_ai_action",
          action: actionType,
          ts: new Date().toISOString(),
        })).reduce((hex, byte) => hex + byte.toString(16).padStart(2, "0"), "0x"),
      });

      const receipt = await tx.wait();
      await updateBalance(state.address);

      return {
        txHash: receipt?.hash,
        blockNumber: receipt?.blockNumber,
        explorerUrl: `${NETWORK.blockExplorerUrls[0]}/transaction/${receipt?.hash}`,
      };
    },
    [state.address, getProvider, updateBalance]
  );

  // Listen for account/chain changes
  useEffect(() => {
    if (!hasMetaMask) return;

    const ethereum = (window as any).ethereum;

    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        disconnect();
      } else {
        setState((prev) => ({ ...prev, address: accounts[0] }));
        updateBalance(accounts[0]);
      }
    };

    const handleChainChanged = () => {
      window.location.reload();
    };

    ethereum.on("accountsChanged", handleAccountsChanged);
    ethereum.on("chainChanged", handleChainChanged);

    return () => {
      ethereum.removeListener("accountsChanged", handleAccountsChanged);
      ethereum.removeListener("chainChanged", handleChainChanged);
    };
  }, [hasMetaMask, disconnect, updateBalance]);

  return {
    ...state,
    hasMetaMask,
    connect,
    disconnect,
    switchToHedera,
    payForAction,
    shortAddress: state.address
      ? `${state.address.slice(0, 6)}...${state.address.slice(-4)}`
      : null,
  };
}
