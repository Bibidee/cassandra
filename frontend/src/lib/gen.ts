const DECIMALS = 18n;
const WEI_PER_GEN = 10n ** DECIMALS;

/**
 * Converts a user-typed GEN amount (e.g. "12.5") into wei as a bigint, for
 * use as `writeContract`'s `value`. Contract fields carrying real GEN
 * (total_coverage, total_liquidity, prophet_cut applied to them) are wei-
 * scale u256 values now that provide_liquidity/buy_coverage are payable -
 * far beyond Number.MAX_SAFE_INTEGER for realistic amounts, so this and
 * `toBigint`/`formatGen` below are the only places that should touch GEN
 * math; never read these fields as plain `number`.
 */
export function toWei(genAmount: string): bigint {
  const trimmed = genAmount.trim();
  if (!trimmed) return BigInt(0);
  const [whole, frac = ""] = trimmed.split(".");
  const paddedFrac = (frac + "0".repeat(Number(DECIMALS))).slice(0, Number(DECIMALS));
  const wholeBig = BigInt(whole || "0") * WEI_PER_GEN;
  const fracBig = BigInt(paddedFrac || "0");
  return wholeBig + fracBig;
}

/** Coerces a contract-returned numeric field (number | bigint) to bigint. */
export function toBigint(value: number | bigint): bigint {
  return typeof value === "bigint" ? value : BigInt(Math.trunc(value));
}

/** Formats a wei-scale bigint as a human GEN string, trimmed to a few decimals. */
export function formatGen(value: number | bigint, maxDecimals = 4): string {
  const wei = toBigint(value);
  const whole = wei / WEI_PER_GEN;
  const remainder = wei % WEI_PER_GEN;
  if (remainder === BigInt(0)) return whole.toLocaleString();

  const fracStr = remainder.toString().padStart(Number(DECIMALS), "0").slice(0, maxDecimals);
  const trimmedFrac = fracStr.replace(/0+$/, "");
  return trimmedFrac ? `${whole.toLocaleString()}.${trimmedFrac}` : whole.toLocaleString();
}

/** Safe ratio of two wei-scale bigints as a 0..1 float, for progress bars. */
export function ratio(numerator: number | bigint, denominator: number | bigint): number {
  const num = toBigint(numerator);
  const den = toBigint(denominator);
  if (den === BigInt(0)) return 0;
  // Scale up before dividing to keep sub-1 precision without floating bigint math.
  return Number((num * BigInt(10000)) / den) / 10000;
}
