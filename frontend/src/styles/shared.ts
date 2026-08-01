import type { CSSProperties } from "react";

export const inputStyle: CSSProperties = {
  background: "var(--surface-raised)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  color: "var(--parchment)",
  padding: "9px 12px",
  fontSize: 13,
  fontFamily: "inherit",
};

export const buttonStyle: CSSProperties = {
  background: "var(--ember)",
  color: "var(--void)",
  fontWeight: 600,
  fontSize: 13,
  padding: "9px 16px",
  borderRadius: "var(--radius)",
  border: "none",
  cursor: "pointer",
};

export const secondaryButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: "transparent",
  border: "1px solid var(--rust)",
  color: "var(--gold)",
};

export const sectionLabelStyle: CSSProperties = {
  fontSize: 11,
  letterSpacing: "0.2em",
  textTransform: "uppercase",
  color: "var(--rust)",
  marginBottom: 16,
};

export const cardStyle: CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-card)",
  padding: 24,
};
