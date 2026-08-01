import { sectionLabelStyle, cardStyle } from "../styles/shared";

const STEPS = [
  {
    title: "1. Seed",
    body: "Someone submits a Warning: a source URL, a verbatim quote, and a category. The source must be public and timestamped before any event it describes - this is what stops post-hoc warnings from being submitted after the fact.",
  },
  {
    title: "2. Forge & Ratify",
    body: "CASSANDRA's leader validator drafts a structured, falsifiable Prophecy from the raw warning: a specific event class, an evidentiary standard, and a resolution window. Reaching validator consensus on that draft - through GenLayer's equivalence-principle mechanism - is the ratification step. No separate vote is needed.",
  },
  {
    title: "3. Underwrite",
    body: "Liquidity providers stake into the pool; buyers pay premium for coverage against the warned-about event.",
  },
  {
    title: "4. Resolve",
    body: "At any point after underwriting, resolution can be triggered with a piece of real-world evidence - a URL. Validators independently fetch and read it, then judge two separate questions: did the event occur, and is it genuinely linked to the original warning (not a coincidence).",
  },
  {
    title: "5. Settle",
    body: "If validators agree the warning was vindicated, coverage holders are paid (minus the prophet's cut, routed to whoever submitted the original warning). If not, premiums are retained by liquidity providers as yield.",
  },
  {
    title: "6. Appeal",
    body: "A disputed resolution can be escalated to a larger validator set for re-judgment.",
  },
];

export default function HowItWorks() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px" }}>
      <div style={sectionLabelStyle}>How it works</div>
      <h1 className="serif" style={{ fontSize: 28, marginBottom: 16 }}>Optimistic Democracy, plainly</h1>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--parchment-dim)", marginBottom: 32 }}>
        CASSANDRA doesn't use a price feed, because there is no price feed for "was this warning
        actually right." Every resolution requires reading comprehension and causal judgment - a
        leader validator proposes an answer, independent validators check it, and only when they
        agree does the answer become final. That's GenLayer's Optimistic Democracy: consensus on
        <em> meaning</em>, not just bytes.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 40 }}>
        {STEPS.map((step) => (
          <div key={step.title} style={cardStyle}>
            <div className="serif" style={{ fontSize: 16, marginBottom: 8 }}>{step.title}</div>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--parchment-dim)" }}>{step.body}</div>
          </div>
        ))}
      </div>

      <h2 className="serif" style={{ fontSize: 20, marginBottom: 12 }}>Why the rationale is always visible</h2>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--parchment-dim)" }}>
        Every resolved prophecy carries its validators' actual reasoning on-chain, in the
        contract's <code style={{ color: "var(--parchment)" }}>resolution_rationale</code> field. It is
        never hidden behind a tooltip and never truncated. Hiding it would undercut the entire
        premise of the product: the whole point is that you can check the reasoning yourself,
        rather than trust a black box.
      </p>
    </div>
  );
}
