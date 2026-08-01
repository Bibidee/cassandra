import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CASSANDRA_ADDRESS, CATEGORIES } from "../config/contracts";
import { TransactionStatus } from "../lib/genlayer-client";
import { useWallet } from "../lib/wallet-context";
import { cardStyle, inputStyle, buttonStyle, sectionLabelStyle } from "../styles/shared";

export default function Submit() {
  const { writeClient } = useWallet();
  const navigate = useNavigate();
  const [sourceUrl, setSourceUrl] = useState("");
  const [quoteText, setQuoteText] = useState("");
  const [category, setCategory] = useState<string>(CATEGORIES[0]);
  const [prophetCutBps, setProphetCutBps] = useState("500");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!writeClient) {
      setStatus("Connect a wallet first.");
      return;
    }
    setBusy(true);
    setStatus("Submitted - waiting for consensus...");
    try {
      const hash = await writeClient.writeContract({
        address: CASSANDRA_ADDRESS,
        functionName: "submit_warning",
        args: [sourceUrl, quoteText, category, Number(prophetCutBps)],
        value: BigInt(0),
      });
      const receipt = await writeClient.waitForTransactionReceipt({
        hash,
        status: TransactionStatus.ACCEPTED,
      });
      setStatus("Finalized. Redirecting...");
      const newId = Number(
        (receipt as { consensus_data?: { leader_receipt?: { result?: { payload?: { readable?: string } } }[] } })
          .consensus_data?.leader_receipt?.[0]?.result?.payload?.readable ?? 0,
      );
      navigate(`/prophecies/${newId}`);
    } catch (err) {
      setStatus(`Failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 560, margin: "0 auto", padding: "32px 24px" }}>
      <div style={sectionLabelStyle}>Seed a new warning</div>
      <p style={{ fontSize: 14, color: "var(--parchment-dim)", lineHeight: 1.6, marginBottom: 24 }}>
        A warning needs a public, timestamped source predating any event it describes. CASSANDRA's
        leader validator will draft it into a falsifiable claim with a resolution window; reaching
        validator consensus on that draft is the ratification step.
      </p>
      <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 12 }}>
        <label className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)" }}>Source URL</label>
        <input placeholder="https://..." value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} style={inputStyle} />

        <label className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)" }}>Quote the warning verbatim</label>
        <textarea
          value={quoteText}
          onChange={(e) => setQuoteText(e.target.value)}
          rows={4}
          style={{ ...inputStyle, resize: "vertical" as const }}
        />

        <label className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)" }}>Category</label>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <label className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)" }}>
          Prophet's cut (basis points, max 2000 = 20%)
        </label>
        <input value={prophetCutBps} onChange={(e) => setProphetCutBps(e.target.value)} style={inputStyle} />

        <button onClick={submit} disabled={busy || !sourceUrl || !quoteText} style={{ ...buttonStyle, marginTop: 8 }}>
          {busy ? "Submitting..." : "Submit warning"}
        </button>
        {status && <div className="mono" style={{ fontSize: 12, color: "var(--parchment-dim)" }}>{status}</div>}
      </div>
    </div>
  );
}
