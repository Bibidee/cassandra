// Deployed CASSANDRA contract on StudioNet (chain id 61999).
// Redeploy notes live in the repo root build brief; update this address
// whenever `genlayer deploy` is run again.
export const CASSANDRA_ADDRESS = (import.meta.env.VITE_CASSANDRA_ADDRESS as `0x${string}`) ?? "0xaa7F8f52228B6001DbC276397B4519F3EA05FFB0";

export const CATEGORIES = [
  "security",
  "climate",
  "depeg",
  "regulatory",
  "systemic",
] as const;

export type Category = (typeof CATEGORIES)[number];

export type ProphecyStatus =
  | "DRAFTING"
  | "RATIFIED"
  | "UNDERWRITING"
  | "ACTIVE"
  | "RESOLVING"
  | "SETTLED"
  | "DISPUTED"
  | "FINAL";

export interface ProphecyState {
  status: ProphecyStatus;
  warning: {
    source_url: string;
    quote_text: string;
    category: string;
    submitter: string;
    submitted_at: string;
  };
  prophecy: {
    structured_claim: string;
    evidentiary_standard: string;
    resolution_window_start: string;
    resolution_window_end: string;
  };
  // Wei-scale u256 values now that provide_liquidity/buy_coverage are
  // payable - genlayer-js may decode these as bigint once they exceed
  // Number.MAX_SAFE_INTEGER. Always read through lib/gen.ts, never
  // format directly.
  total_coverage: number | bigint;
  total_liquidity: number | bigint;
  prophet_cut_bps: number; // basis points, small int, not wei-scale
}
