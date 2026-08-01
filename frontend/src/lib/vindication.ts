/**
 * The contract's SETTLED status means "resolution completed," not "the
 * warning came true" - a prophecy can settle as vindicated (payout to
 * coverage holders) or not vindicated (premiums retained by LPs). The
 * settlement outcome is only encoded as a suffix in the rationale string
 * ("| SETTLED: vindicated, ..." vs "| SETTLED: not vindicated, ..."),
 * since get_prophecy_state does not expose resolution.occurred/linked
 * directly. This helper is the single source of truth for that check -
 * never infer vindication from status alone.
 */
export function isVindicated(rationale: string): boolean {
  return /\|\s*SETTLED:\s*vindicated/i.test(rationale);
}

export function isResolvedNotVindicated(status: string, rationale: string): boolean {
  return (status === "SETTLED" || status === "FINAL") && !isVindicated(rationale);
}
