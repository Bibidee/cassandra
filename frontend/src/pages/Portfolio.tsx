import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useWallet } from "../lib/wallet-context";
import { useProphecies } from "../lib/useProphecies";
import { fetchCoverageOf, fetchLiquidityOf, pooled } from "../lib/prophecies";
import { formatGen, toBigint } from "../lib/gen";
import { sectionLabelStyle, cardStyle, secondaryButtonStyle } from "../styles/shared";

interface Position {
  id: number;
  category: string;
  status: string;
  coverage: number | bigint;
  liquidity: number | bigint;
}

export default function Portfolio() {
  const { address, connect } = useWallet();
  const { prophecies, loading: prophesiesLoading } = useProphecies();
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!address || prophesiesLoading) return;
    setLoading(true);
    (async () => {
      const tasks = prophecies.map((p) => async () => {
        const [coverage, liquidity] = await Promise.all([
          fetchCoverageOf(p.id, address),
          fetchLiquidityOf(p.id, address),
        ]);
        return { id: p.id, category: p.state.warning.category, status: p.state.status, coverage, liquidity } as Position;
      });
      const raw = await pooled(tasks, 4);
      const results: Position[] = (raw.filter(Boolean) as Position[])
        .filter((pos) => toBigint(pos.coverage) > BigInt(0) || toBigint(pos.liquidity) > BigInt(0));
      setPositions(results);
      setLoading(false);
    })();
  }, [address, prophecies, prophesiesLoading]);

  if (!address) {
    return (
      <div style={{ maxWidth: 560, margin: "0 auto", padding: "32px 24px", textAlign: "center" }}>
        <div style={sectionLabelStyle}>Your portfolio</div>
        <p style={{ color: "var(--parchment-dim)", marginBottom: 20 }}>Connect a wallet to see your positions.</p>
        <button style={secondaryButtonStyle} onClick={connect}>Connect wallet</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px" }}>
      <div style={sectionLabelStyle}>Your portfolio</div>
      {(loading || prophesiesLoading) && <div className="mono" style={{ color: "var(--parchment-dim)" }}>Loading...</div>}
      {!loading && !prophesiesLoading && positions.length === 0 && (
        <p className="serif" style={{ fontStyle: "italic", color: "var(--parchment-dim)" }}>
          No positions yet. The silence before the warning.
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {positions.map((pos) => (
          <Link key={pos.id} to={`/prophecies/${pos.id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <div style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div className="mono" style={{ fontSize: 11, color: "var(--rust)", textTransform: "uppercase" }}>
                  {pos.category} · #{pos.id}
                </div>
                <div className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)", marginTop: 4 }}>{pos.status}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                {toBigint(pos.coverage) > BigInt(0) && (
                  <div className="mono" style={{ fontSize: 13 }}>{formatGen(pos.coverage)} GEN coverage</div>
                )}
                {toBigint(pos.liquidity) > BigInt(0) && (
                  <div className="mono" style={{ fontSize: 13, color: "var(--gold)" }}>{formatGen(pos.liquidity)} GEN underwritten</div>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
