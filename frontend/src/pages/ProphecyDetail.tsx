import { useParams, Link } from "react-router-dom";
import { useProphecy } from "../lib/useProphecy";
import { ProphecyCard } from "../components/ProphecyCard";
import { ProphecyActions } from "../components/ProphecyActions";

export default function ProphecyDetail() {
  const { id } = useParams<{ id: string }>();
  const prophecyId = Number(id);
  const { entry, loading, error, refresh } = useProphecy(prophecyId);

  if (loading) {
    return <div className="mono" style={{ padding: 32, color: "var(--parchment-dim)" }}>Loading...</div>;
  }

  if (error || !entry) {
    return (
      <div style={{ padding: 32 }}>
        <p className="serif" style={{ fontStyle: "italic" }}>The oracle is unclear. Try again.</p>
        <Link to="/prophecies" className="mono" style={{ color: "var(--gold)", fontSize: 12 }}>
          &larr; Back to prophecies
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/prophecies" className="mono" style={{ color: "var(--parchment-dim)", fontSize: 12, textDecoration: "none" }}>
        &larr; All prophecies
      </Link>
      <div style={{ marginTop: 20 }}>
        <ProphecyCard id={entry.id} state={entry.state} rationale={entry.rationale}>
          <ProphecyActions entry={entry} onChanged={refresh} />
        </ProphecyCard>
      </div>
      <div style={{ marginTop: 20 }}>
        <Link
          to={`/prophet/${entry.state.warning.submitter}`}
          className="mono"
          style={{ fontSize: 12, color: "var(--parchment-dim)" }}
        >
          View this prophet's track record &rarr;
        </Link>
      </div>
    </div>
  );
}
