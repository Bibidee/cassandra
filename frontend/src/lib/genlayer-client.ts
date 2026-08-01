import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const rpcUrl = import.meta.env.VITE_GENLAYER_RPC ?? studionet.rpcUrls.default.http[0];
const chainId = import.meta.env.VITE_GENLAYER_CHAIN_ID
  ? Number(import.meta.env.VITE_GENLAYER_CHAIN_ID)
  : studionet.id;

export const chain: typeof studionet = {
  ...studionet,
  id: chainId,
  rpcUrls: {
    default: { http: [rpcUrl] },
  },
};

// Read client: no wallet needed, talks directly to the configured RPC.
export const readClient = createClient({ chain });

export { TransactionStatus };

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
      on?: (event: string, handler: (...args: unknown[]) => void) => void;
      removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
    };
  }
}

const STUDIONET_CHAIN_ID_HEX = `0x${chain.id.toString(16)}`;

/**
 * Switches the injected wallet to StudioNet using the standard EIP-3326
 * (wallet_switchEthereumChain) / EIP-3085 (wallet_addEthereumChain) RPC
 * methods. Deliberately NOT genlayer-js's `client.connect()` - that helper
 * calls MetaMask's Snaps API (`wallet_getSnaps`) internally, which plain
 * injected wallets (Rabby, and MetaMask without a snap installed) do not
 * implement, and throws "method [wallet_getSnaps] doesn't have a
 * corresponding handler". This app targets the standard injected-provider
 * surface only, not MetaMask Snaps.
 */
async function switchToStudioNet(ethereum: NonNullable<Window["ethereum"]>): Promise<void> {
  try {
    await ethereum.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: STUDIONET_CHAIN_ID_HEX }],
    });
  } catch (err) {
    const code = (err as { code?: number })?.code;
    if (code !== 4902) throw err; // 4902 = chain not added yet
    await ethereum.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: STUDIONET_CHAIN_ID_HEX,
          chainName: chain.name,
          nativeCurrency: chain.nativeCurrency,
          rpcUrls: chain.rpcUrls.default.http,
          blockExplorerUrls: chain.blockExplorers?.default
            ? [chain.blockExplorers.default.url]
            : undefined,
        },
      ],
    });
  }
}

function buildWriteClient(address: `0x${string}`) {
  return createClient({
    chain,
    account: address,
    provider: window.ethereum,
  });
}

/**
 * Connects to an injected wallet (MetaMask, Rabby, or any EIP-1193
 * provider), switches it to StudioNet via standard chain-switch RPC calls,
 * and returns a write-capable client bound to the connected account. Uses
 * `eth_requestAccounts`, which prompts the wallet's connect UI - call this
 * only in response to a direct user action (a "Connect wallet" click).
 */
export async function connectWallet(): Promise<{ address: `0x${string}`; writeClient: ReturnType<typeof createClient> }> {
  if (!window.ethereum) {
    throw new Error("No injected wallet found. Install MetaMask, Rabby, or a compatible wallet.");
  }

  const accounts = (await window.ethereum.request({
    method: "eth_requestAccounts",
  })) as string[];

  const address = accounts[0] as `0x${string}`;
  await switchToStudioNet(window.ethereum);

  return { address, writeClient: buildWriteClient(address) };
}

/**
 * Restores a previously-authorized wallet session without prompting the
 * user. Uses `eth_accounts` (never `eth_requestAccounts`) - it only returns
 * accounts the site is already permitted to see, so it's safe to call on
 * every page load. Returns null if no account is already authorized.
 */
export async function reconnectWallet(): Promise<{ address: `0x${string}`; writeClient: ReturnType<typeof createClient> } | null> {
  if (!window.ethereum) return null;

  const accounts = (await window.ethereum.request({ method: "eth_accounts" })) as string[];
  if (!accounts.length) return null;

  const address = accounts[0] as `0x${string}`;
  return { address, writeClient: buildWriteClient(address) };
}
