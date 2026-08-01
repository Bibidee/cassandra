import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { useProphecies } from "../lib/useProphecies";
import { isVindicated } from "../lib/vindication";
import { sectionLabelStyle, cardStyle } from "../styles/shared";

const RESOLVED = new Set(["SETTLED", "FINAL", "DISPUTED"]);

export default function Prophet() {
  const { address } = useParams<{ address: string }>();
  const { prophecies, loading } = useProphecies();

  const authored = useMemo(
    () => prophecies.filter((p) => p.state.warning.submitter.toLowerCase() === address?.toLowerCase()),
    [prophecies, address],
  );

  const resolved = authored.filter((p) => RESOLVED.has(p.state.status));
  const vindicated = authored.filter((p) => isVindicated(p.rationale));
  const winRate = resolved.length > 0 ? Math.round((vindicated.length / resolved.length) * 100) : null;

  const byCategory = useMemo(() => {
    const map: Record<string, number> = {};
    for (const p of authored) {
      map[p.state.warning.category] = (map[p.state.warning.category] ?? 0) + 1;
    }
    return map;
  }, [authored]);

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px" }}>
      <div style={sectionLabelStyle}>Prophet track record</div>
      <div className="mono" style={{ fontSize: 13, color: "var(--parchment-dim)", marginBottom: 24 }}>
        {address}
      </div>

      {loading && <div className="mono" style={{ color: "var(--parchment-dim)" }}>Loading...</div>}

      {!loading && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 32 }}>
            <div style={cardStyle}>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-faint)", textTransform: "uppercase", marginBottom: 6 }}>
                Warnings submitted
              </div>
              <div className="serif" style={{ fontSize: 24 }}>{authored.length}</div>
            </div>
            <div style={cardStyle}>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-faint)", textTransform: "uppercase", marginBottom: 6 }}>
                Resolved
              </div>
              <div className="serif" style={{ fontSize: 24 }}>{resolved.length}</div>
            </div>
            <div style={cardStyle}>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-faint)", textTransform: "uppercase", marginBottom: 6 }}>
                Win rate
              </div>
              <div className="serif" style={{ fontSize: 24, color: "var(--sage)" }}>
                {winRate === null ? "-" : `${winRate}%`}
              </div>
            </div>
          </div>

          <div style={sectionLabelStyle}>By category</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 32 }}>
            {Object.entries(byCategory).map(([cat, count]) => (
              <span
                key={cat}
                className="mono"
                style={{ fontSize: 11, padding: "4px 10px", borderRadius: 20, background: "rgba(196,96,42,0.12)", color: "var(--rust)" }}
              >
                {cat} · {count}
              </span>
            ))}
          </div>

          <div style={sectionLabelStyle}>Warnings</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {authored.map((p) => (
              <Link key={p.id} to={`/prophecies/${p.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                <div style={{ ...cardStyle, padding: 16 }}>
                  <div
                    className="mono"
                    style={{
                      fontSize: 11,
                      color: isVindicated(p.rationale) ? "var(--sage)" : "var(--gold)",
                      marginBottom: 6,
                    }}
                  >
                    #{p.id} · {p.state.status}
                    {RESOLVED.has(p.state.status) && (isVindicated(p.rationale) ? " · vindicated" : " · not vindicated")}
                  </div>
                  <p className="serif" style={{ fontStyle: "italic", fontSize: 13, margin: 0 }}>
                    &ldquo;{p.state.warning.quote_text}&rdquo;
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
