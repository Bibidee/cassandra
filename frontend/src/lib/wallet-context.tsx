import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { connectWallet, reconnectWallet } from "./genlayer-client";

type WriteClient = Awaited<ReturnType<typeof connectWallet>>["writeClient"];

interface WalletContextValue {
  address: string | null;
  writeClient: WriteClient | null;
  connectError: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
}

const WalletContext = createContext<WalletContextValue | null>(null);

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [writeClient, setWriteClient] = useState<WriteClient | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setConnectError(null);
    try {
      const { address, writeClient } = await connectWallet();
      setAddress(address);
      setWriteClient(writeClient);
    } catch (err) {
      setConnectError((err as Error).message);
    }
  }, []);

  const disconnect = useCallback(() => {
    // Injected wallets (MetaMask, Rabby) expose no real "disconnect" RPC -
    // the site remains authorized until the user revokes it from the
    // wallet's own UI. This clears our local session only, so the app
    // stops using the account until the user reconnects explicitly.
    setAddress(null);
    setWriteClient(null);
    setConnectError(null);
  }, []);

  // Silently restore an already-authorized session on load (eth_accounts,
  // no popup) - the wallet should not appear "disconnected" on refresh.
  useEffect(() => {
    let cancelled = false;
    reconnectWallet().then((session) => {
      if (cancelled || !session) return;
      setAddress(session.address);
      setWriteClient(session.writeClient);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // If the user switches or disconnects accounts from the wallet's own UI,
  // reflect that immediately instead of holding a stale address.
  useEffect(() => {
    if (!window.ethereum?.on) return;
    const handleAccountsChanged = (...args: unknown[]) => {
      const accounts = args[0] as string[];
      if (accounts.length === 0) {
        disconnect();
        return;
      }
      // Already authorized - rebuild the client with eth_accounts (no
      // popup) rather than eth_requestAccounts, which would re-prompt.
      reconnectWallet().then((session) => {
        if (!session) return;
        setAddress(session.address);
        setWriteClient(session.writeClient);
      });
    };
    window.ethereum.on("accountsChanged", handleAccountsChanged);
    return () => {
      window.ethereum?.removeListener?.("accountsChanged", handleAccountsChanged);
    };
  }, [disconnect]);

  return (
    <WalletContext.Provider value={{ address, writeClient, connectError, connect, disconnect }}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}
