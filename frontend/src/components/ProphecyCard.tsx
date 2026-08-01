import type { ProphecyState } from "../config/contracts";
import { SealGlyph } from "./SealGlyph";
import { FlameProgress } from "./FlameProgress";
import { ResolutionRationale } from "./ResolutionRationale";
import { isVindicated, isResolvedNotVindicated } from "../lib/vindication";
import { formatGen, ratio, toBigint } from "../lib/gen";

interface ProphecyCardProps {
  id: number;
  state: ProphecyState;
  rationale: string;
  children?: React.ReactNode; // action buttons, injected by the page
}

const STATUS_LABEL: Record<string, string> = {
  DRAFTING: "Drafting",
  RATIFIED: "Ratified",
  UNDERWRITING: "Underwriting",
  ACTIVE: "Active",
  RESOLVING: "Resolving",
  SETTLED: "Settled",
  DISPUTED: "Disputed",
  FINAL: "Final",
};

export function ProphecyCard({ id, state, rationale, children }: ProphecyCardProps) {
  const vindicated = isVindicated(rationale);
  const settledFalse = isResolvedNotVindicated(state.status, rationale);
  const statusLabel = settledFalse
    ? "Settled - not vindicated"
    : vindicated
      ? "Settled - vindicated"
      : STATUS_LABEL[state.status] ?? state.status;
  const fillFraction = ratio(state.total_coverage, state.total_liquidity);
  const hasLiquidity = toBigint(state.total_liquidity) > BigInt(0);

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-card)",
        padding: 24,
        position: "relative",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 18 }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "var(--rust)",
            background: "rgba(196,96,42,0.12)",
            padding: "4px 8px",
            borderRadius: 5,
          }}
        >
          {state.warning.category} · #{id}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 10,
            padding: "4px 9px",
            borderRadius: 20,
            color: vindicated ? "var(--sage)" : settledFalse ? "var(--rust)" : "var(--gold)",
            background: vindicated
              ? "rgba(74,140,126,0.12)"
              : settledFalse
                ? "rgba(196,96,42,0.12)"
                : "rgba(245,200,66,0.1)",
          }}
        >
          {statusLabel}
        </span>
      </div>

      <p
        className="serif"
        style={{
          fontStyle: "italic",
          fontSize: 15,
          lineHeight: 1.55,
          borderLeft: "2px solid var(--rust)",
          paddingLeft: 14,
          margin: "0 0 16px",
        }}
      >
        &ldquo;{state.warning.quote_text}&rdquo;
      </p>

      {state.prophecy.structured_claim && (
        <div className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)", marginBottom: 6 }}>
          Claim: <span style={{ color: "var(--parchment)" }}>{state.prophecy.structured_claim}</span>
        </div>
      )}
      <div className="mono" style={{ fontSize: 11, color: "var(--parchment-dim)", marginBottom: 6 }}>
        Source: <span style={{ color: "var(--parchment)" }}>{state.warning.source_url}</span>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 20,
          paddingTop: 16,
          borderTop: "1px solid var(--border)",
        }}
      >
        <div className="mono" style={{ fontSize: 13 }}>
          <span style={{ display: "block", fontSize: 10, color: "var(--ink-faint)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 3 }}>
            Pool
          </span>
          {formatGen(state.total_liquidity)} GEN
        </div>
        <SealGlyph vindicated={vindicated} />
      </div>

      {hasLiquidity && (
        <div style={{ marginTop: 14 }}>
          <FlameProgress
            fraction={fillFraction}
            vindicated={vindicated}
            label={
              vindicated
                ? "VINDICATED"
                : settledFalse
                  ? "NOT VINDICATED"
                  : `${formatGen(state.total_coverage)} / ${formatGen(state.total_liquidity)} GEN COVERED`
            }
          />
        </div>
      )}

      <ResolutionRationale rationale={rationale} />

      {children && <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>{children}</div>}
    </div>
  );
}
