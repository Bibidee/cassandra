import { NavLink } from "react-router-dom";
import { useWallet } from "../lib/wallet-context";
import { secondaryButtonStyle } from "../styles/shared";

const links = [
  { to: "/prophecies", label: "Prophecies" },
  { to: "/submit", label: "Submit a warning" },
  { to: "/portfolio", label: "Portfolio" },
  { to: "/how-it-works", label: "How it works" },
];

export function Nav() {
  const { address, connectError, connect, disconnect } = useWallet();

  return (
    <nav
      style={{
        maxWidth: 960,
        margin: "0 auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "24px 24px 0",
      }}
    >
      <NavLink to="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
        <img src="/logo.svg" alt="CASSANDRA" width={32} height={32} />
        <span className="serif" style={{ fontWeight: 700, fontSize: 19, color: "var(--parchment)" }}>CASSANDRA</span>
      </NavLink>
      <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className="mono"
            style={({ isActive }) => ({
              fontSize: 12,
              textDecoration: "none",
              color: isActive ? "var(--gold)" : "var(--parchment-dim)",
            })}
          >
            {l.label}
          </NavLink>
        ))}
        {address ? (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ ...secondaryButtonStyle, cursor: "default" }}>
              {`${address.slice(0, 6)}...${address.slice(-4)}`}
            </span>
            <button
              style={{ ...secondaryButtonStyle, padding: "9px 12px" }}
              onClick={disconnect}
              aria-label="Disconnect wallet"
              title="Disconnect wallet"
            >
              &times;
            </button>
          </div>
        ) : (
          <button style={secondaryButtonStyle} onClick={connect}>
            Connect wallet
          </button>
        )}
      </div>
      {connectError && (
        <div className="mono" style={{ position: "fixed", top: 8, right: 24, fontSize: 11, color: "var(--ember)" }}>
          {connectError}
        </div>
      )}
    </nav>
  );
}
