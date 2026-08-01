interface ResolutionRationaleProps {
  rationale: string;
}

/**
 * Verbatim on-chain validator rationale - CASSANDRA's trust mechanism.
 * Never truncated: this is deliberately the least "designed" component
 * in the app because the content itself is the point.
 */
export function ResolutionRationale({ rationale }: ResolutionRationaleProps) {
  if (!rationale) return null;

  return (
    <div
      style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: "1px solid var(--border)",
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--rust)",
          marginBottom: 8,
        }}
      >
        Validator rationale
      </div>
      <p
        className="serif"
        style={{
          fontSize: 14,
          lineHeight: 1.6,
          color: "var(--parchment)",
          margin: 0,
          whiteSpace: "pre-wrap",
        }}
      >
        {rationale}
      </p>
    </div>
  );
}
