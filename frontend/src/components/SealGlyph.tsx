interface SealGlyphProps {
  vindicated: boolean;
  size?: number;
}

/**
 * Procedural seal glyph: dashed/muted while a prophecy is unresolved OR
 * resolved-but-not-vindicated, solid gold only when the warning was
 * actually vindicated - the "prophecy fulfilled" visual signature from
 * the design spec. Vindication must be passed in explicitly (see
 * lib/vindication.ts) - it is not derivable from status alone, since
 * SETTLED covers both outcomes.
 */
export function SealGlyph({ vindicated, size = 34 }: SealGlyphProps) {
  const stroke = vindicated ? "#f5c842" : "#8a7a60";
  const dash = vindicated ? undefined : "2 2";
  const width = vindicated ? 1.6 : 1.2;

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke={stroke} strokeWidth={width} strokeDasharray={dash} />
      <path d="M12 6v6l4 2" stroke={stroke} strokeWidth={width} strokeLinecap="round" />
    </svg>
  );
}
