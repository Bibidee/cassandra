interface FlameProgressProps {
  fraction: number; // 0..1
  vindicated?: boolean;
  label: string;
}

/** Ember-gradient progress bar used for underwriting fill and settlement state. */
export function FlameProgress({ fraction, vindicated, label }: FlameProgressProps) {
  const pct = Math.max(0, Math.min(1, fraction)) * 100;
  const gradient = vindicated
    ? "linear-gradient(90deg, var(--sage), var(--gold))"
    : "linear-gradient(90deg, var(--ember), var(--gold))";

  return (
    <div>
      <div
        style={{
          height: 4,
          borderRadius: 2,
          background: "var(--surface-raised)",
          overflow: "hidden",
        }}
      >
        <div style={{ height: "100%", width: `${pct}%`, background: gradient, borderRadius: 2 }} />
      </div>
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: vindicated ? "var(--sage)" : "var(--ink-faint)",
          marginTop: 8,
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </div>
    </div>
  );
}
