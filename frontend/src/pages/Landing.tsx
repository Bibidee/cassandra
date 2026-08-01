import { Link } from "react-router-dom";
import { useProphecies } from "../lib/useProphecies";
import { SealGlyph } from "../components/SealGlyph";
import { isVindicated } from "../lib/vindication";
import { buttonStyle, secondaryButtonStyle, cardStyle } from "../styles/shared";
import { CATEGORIES } from "../config/contracts";

const CATEGORY_COPY: Record<string, string> = {
  security: "Audit flags a vulnerability class in a live contract",
  climate: "Climate model warns of drought or flood risk",
  depeg: "Analyst warns a stablecoin's backing is impaired",
  regulatory: "Legal analysis warns of hostile jurisdictional action",
  systemic: "Risk report warns of a correlated cascade",
};

export default function Landing() {
  const { prophecies, loading } = useProphecies();
  const settled = prophecies.find((p) => p.state.status === "SETTLED" || p.state.status === "FINAL");

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "72px 24px" }}>
      <section style={{ textAlign: "center", marginBottom: 72 }}>
        <p className="mono" style={{ fontSize: 11, letterSpacing: "0.32em", textTransform: "uppercase", color: "var(--rust)", marginBottom: 24 }}>
          Parametric insurance, adjudicated by AI consensus
        </p>
        <h1
          className="serif"
          style={{
            fontSize: 48,
            lineHeight: 1.1,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            maxWidth: 720,
            margin: "0 auto 22px",
          }}
        >
          Every warning that came true, and{" "}
          <span
            style={{
              background: "linear-gradient(135deg, #e84d0e 0%, #f5c842 50%, #c4602a 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontStyle: "italic",
            }}
          >
            nobody paid
          </span>{" "}
          for it. Until now.
        </h1>
        <p style={{ fontSize: 16, lineHeight: 1.65, color: "var(--parchment-dim)", maxWidth: 480, margin: "0 auto 36px" }}>
          CASSANDRA insures against ignored warnings: exploits, depegs, climate risk - resolved by
          GenLayer's AI-validator consensus, not a single arbiter.
        </p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center" }}>
          <Link to="/prophecies" style={{ ...buttonStyle, textDecoration: "none" }}>
            Insure against a warning
          </Link>
          <Link to="/submit" style={{ ...secondaryButtonStyle, textDecoration: "none" }}>
            Underwrite a pool
          </Link>
        </div>
      </section>

      {!loading && prophecies.length > 0 && (
        <section
          style={{
            borderTop: "1px solid var(--border)",
            borderBottom: "1px solid var(--border)",
            padding: "14px 0",
            marginBottom: 72,
            overflow: "hidden",
          }}
        >
          <div className="mono" style={{ display: "flex", gap: 40, fontSize: 12, color: "var(--ink-faint)", whiteSpace: "nowrap", overflowX: "auto" }}>
            <span>LIVE PROPHECIES</span>
            {prophecies.slice(0, 6).map((p) => (
              <Link key={p.id} to={`/prophecies/${p.id}`} style={{ color: "var(--gold)", textDecoration: "none" }}>
                #{p.id} {p.state.warning.category}: {p.state.warning.quote_text.slice(0, 40)}...
              </Link>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginBottom: 72 }}>
        <p className="mono" style={{ fontSize: 11, letterSpacing: "0.28em", textTransform: "uppercase", color: "var(--rust)", textAlign: "center", marginBottom: 8 }}>
          The mechanism
        </p>
        <h2 className="serif" style={{ fontSize: 28, textAlign: "center", marginBottom: 48 }}>
          How a prophecy resolves
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
          {[
            { title: "The warning is recorded", desc: "A sourced, timestamped warning is submitted and drafted into a falsifiable claim by the leader validator." },
            { title: "Validators reach consensus", desc: "Independent AI validators judge occurrence and causal linkage - Optimistic Democracy, not a single arbiter." },
            { title: "The pool settles", desc: "Vindicated warnings trigger payout. The rationale stays on-chain, in full, for anyone to read." },
          ].map((step) => (
            <div key={step.title} style={{ textAlign: "center", padding: "0 12px" }}>
              <div className="serif" style={{ fontSize: 17, marginBottom: 8 }}>{step.title}</div>
              <div style={{ fontSize: 13, color: "var(--parchment-dim)", lineHeight: 1.6 }}>{step.desc}</div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 72 }}>
        <p className="mono" style={{ fontSize: 11, letterSpacing: "0.28em", textTransform: "uppercase", color: "var(--rust)", textAlign: "center", marginBottom: 8 }}>
          Launch verticals
        </p>
        <h2 className="serif" style={{ fontSize: 28, textAlign: "center", marginBottom: 48 }}>
          Five categories, one adjudication engine
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
          {CATEGORIES.map((cat) => (
            <div key={cat} style={cardStyle}>
              <div className="mono" style={{ fontSize: 11, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 8 }}>
                {cat}
              </div>
              <div style={{ fontSize: 13, color: "var(--parchment-dim)", lineHeight: 1.5 }}>{CATEGORY_COPY[cat]}</div>
            </div>
          ))}
        </div>
      </section>

      {settled && (
        <section style={{ marginBottom: 72 }}>
          <p className="mono" style={{ fontSize: 11, letterSpacing: "0.28em", textTransform: "uppercase", color: "var(--rust)", textAlign: "center", marginBottom: 8 }}>
            Not a black box
          </p>
          <h2 className="serif" style={{ fontSize: 28, textAlign: "center", marginBottom: 32 }}>
            Every resolution shows its reasoning
          </h2>
          <div style={{ ...cardStyle, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20 }}>
            <div>
              <div className="mono" style={{ fontSize: 11, color: "var(--sage)", marginBottom: 6 }}>SETTLED · #{settled.id}</div>
              <p className="serif" style={{ fontStyle: "italic", margin: 0 }}>&ldquo;{settled.state.warning.quote_text}&rdquo;</p>
            </div>
            <SealGlyph vindicated={isVindicated(settled.rationale)} size={44} />
          </div>
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Link to={`/prophecies/${settled.id}`} className="mono" style={{ fontSize: 12, color: "var(--gold)" }}>
              Read the full rationale &rarr;
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
