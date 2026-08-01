import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useProphecies } from "../lib/useProphecies";
import { ProphecyCard } from "../components/ProphecyCard";
import { CATEGORIES, type ProphecyStatus } from "../config/contracts";
import { sectionLabelStyle, inputStyle } from "../styles/shared";

const STATUSES: ProphecyStatus[] = [
  "DRAFTING",
  "RATIFIED",
  "UNDERWRITING",
  "ACTIVE",
  "RESOLVING",
  "SETTLED",
  "DISPUTED",
  "FINAL",
];

export default function Prophecies() {
  const { prophecies, loading } = useProphecies();
  const [category, setCategory] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");

  const filtered = useMemo(
    () =>
      prophecies.filter((p) => {
        if (category !== "all" && p.state.warning.category !== category) return false;
        if (status !== "all" && p.state.status !== status) return false;
        return true;
      }),
    [prophecies, category, status],
  );

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "32px 24px" }}>
      <div style={sectionLabelStyle}>Browse pools</div>
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle}>
          <option value="all">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={inputStyle}>
          <option value="all">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {loading && <div className="mono" style={{ color: "var(--parchment-dim)" }}>Loading...</div>}
      {!loading && filtered.length === 0 && (
        <div className="serif" style={{ fontStyle: "italic", color: "var(--parchment-dim)" }}>
          No prophecies yet. The silence before the warning.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {filtered.map((entry) => (
          <Link key={entry.id} to={`/prophecies/${entry.id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <ProphecyCard id={entry.id} state={entry.state} rationale={entry.rationale} />
          </Link>
        ))}
      </div>
    </div>
  );
}
