import { useState } from "react";
import type { CalldataEncodable } from "genlayer-js/types";
import { TransactionStatus } from "../lib/genlayer-client";
import { CASSANDRA_ADDRESS } from "../config/contracts";
import type { ProphecyEntry } from "../lib/prophecies";
import { useWallet } from "../lib/wallet-context";
import { toWei } from "../lib/gen";
import { inputStyle, buttonStyle } from "../styles/shared";

export function ProphecyActions({
  entry,
  onChanged,
}: {
  entry: ProphecyEntry;
  onChanged: () => void;
}) {
  const { writeClient } = useWallet();
  const [busy, setBusy] = useState<string | null>(null);
  const [amount, setAmount] = useState("1"); // GEN, not wei - converted via toWei below
  const [evidenceUrl, setEvidenceUrl] = useState("");

  // `value` is the real GEN sent with the transaction - `provide_liquidity`
  // and `buy_coverage` are @gl.public.write.payable on the contract and
  // read gl.message.value directly, they no longer take an amount argument.
  // draft_prophecy and trigger_resolution run non-deterministic validator
  // consensus - the state only updates after FINALIZED (all validators agree).
  // Other writes (provide_liquidity, buy_coverage, settle) are deterministic
  // and safe to read back after ACCEPTED.
  const NEEDS_FINALIZED = new Set(["draft_prophecy", "trigger_resolution"]);

  const call = async (functionName: string, args: CalldataEncodable[], value: bigint = BigInt(0)) => {
    if (!writeClient) return;
    setBusy(functionName);
    try {
      const hash = await writeClient.writeContract({
        address: CASSANDRA_ADDRESS,
        functionName,
        args,
        value,
      });
      await writeClient.waitForTransactionReceipt({
        hash,
        status: NEEDS_FINALIZED.has(functionName)
          ? TransactionStatus.FINALIZED
          : TransactionStatus.ACCEPTED,
      });
      onChanged();
    } finally {
      setBusy(null);
    }
  };

  const { status } = entry.state;

  if (!writeClient) {
    return (
      <div className="mono" style={{ fontSize: 12, color: "var(--ink-faint)" }}>
        Connect a wallet to act on this prophecy.
      </div>
    );
  }

  return (
    <>
      {status === "DRAFTING" && (
        <button style={buttonStyle} disabled={!!busy} onClick={() => call("draft_prophecy", [entry.id])}>
          {busy === "draft_prophecy" ? "Drafting..." : "Draft prophecy"}
        </button>
      )}
      {(status === "RATIFIED" || status === "UNDERWRITING" || status === "ACTIVE") && busy !== "trigger_resolution" && (
        <>
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="GEN amount"
            style={{ ...inputStyle, width: 100 }}
          />
          <button
            style={buttonStyle}
            disabled={!!busy}
            onClick={() => call("provide_liquidity", [entry.id], toWei(amount))}
          >
            {busy === "provide_liquidity" ? "..." : "Underwrite"}
          </button>
        </>
      )}
      {(status === "UNDERWRITING" || status === "ACTIVE") && busy !== "trigger_resolution" && (
        <button
          style={buttonStyle}
          disabled={!!busy}
          onClick={() => call("buy_coverage", [entry.id], toWei(amount))}
        >
          {busy === "buy_coverage" ? "..." : "Buy coverage"}
        </button>
      )}
      {status === "ACTIVE" && (
        <>
          <input
            placeholder="Evidence URL"
            value={evidenceUrl}
            onChange={(e) => setEvidenceUrl(e.target.value)}
            style={{ ...inputStyle, width: 220 }}
          />
          <button
            style={buttonStyle}
            disabled={!!busy || !evidenceUrl}
            onClick={() => call("trigger_resolution", [entry.id, evidenceUrl])}
          >
            {busy === "trigger_resolution" ? "Resolving..." : "Resolve"}
          </button>
        </>
      )}
      {status === "RESOLVING" && (
        <button style={buttonStyle} disabled={!!busy} onClick={() => call("settle", [entry.id])}>
          {busy === "settle" ? "Settling..." : "Settle"}
        </button>
      )}
    </>
  );
}
