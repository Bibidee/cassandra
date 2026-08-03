# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *


# --- Status is stored as a plain string; GenVM storage does not support Enum
# (confirmed against the shipped intelligent_oracle.py reference example). ---
STATUS_DRAFTING = "DRAFTING"
STATUS_RATIFIED = "RATIFIED"
STATUS_UNDERWRITING = "UNDERWRITING"
STATUS_ACTIVE = "ACTIVE"
STATUS_RESOLVING = "RESOLVING"
STATUS_SETTLED = "SETTLED"
STATUS_DISPUTED = "DISPUTED"

# Per-category evidentiary guidance (design spec section 8, open question 4):
# gives the drafting LLM a consistent standard per launch vertical instead of
# inventing one ad hoc each time, so validators judge Occurrence against the
# same bar for the same category across every Prophecy.
CATEGORY_EVIDENTIARY_GUIDANCE = {
    "security": (
        "Prefer on-chain evidence: transaction hashes, block explorer records, "
        "or a post-mortem/incident report from the affected protocol or a "
        "recognized security firm."
    ),
    "depeg": (
        "Prefer on-chain price/oracle data showing the peg deviation, or a "
        "reserve-attestation report from the stablecoin issuer or an "
        "independent auditor."
    ),
    "regulatory": (
        "Prefer an official government, court, or regulator publication "
        "(statute, ruling, enforcement action, or press release) matching "
        "the warned jurisdiction and scope."
    ),
    "climate": (
        "Prefer verified meteorological or hydrological data from a "
        "recognized agency (national weather service, NOAA, remote sensing "
        "data) for the warned region and window."
    ),
    "systemic": (
        "Prefer correlated on-chain or market data across the warned "
        "dependency chain, or a risk report from a recognized analyst "
        "confirming the cascade matches the warned mechanism."
    ),
}
DEFAULT_EVIDENTIARY_GUIDANCE = (
    "Prefer the most authoritative, independently verifiable source "
    "available for this category."
)


@gl.evm.contract_interface
class _Recipient:
    """
    Generic EVM-interface proxy used only for its built-in `emit_transfer`
    (native GEN transfer, no calldata) - the standard GenVM pattern for
    paying out a plain address, verified against the same pinned SDK
    version we deploy against. Empty View/Write blocks are correct: this
    interface declares no callable methods of its own, since we only ever
    use the ContractProxy base's built-in `emit_transfer`/`balance`.
    """

    class View:
        pass

    class Write:
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(value: str) -> datetime:
    """
    Parses an ISO 8601 date/datetime string (the LLM is asked for plain
    "YYYY-MM-DD" but may occasionally include a time component) into an
    aware UTC datetime, so resolution-window checks compare like with like.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise gl.vm.UserError(f"EXPECTED: invalid ISO date '{value}' in resolution window")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _strict_bool(value: object, field_name: str) -> bool:
    """
    Rejects anything that isn't a literal JSON boolean. `bool("false")` is
    True in Python (any non-empty string is truthy) - if an LLM response
    ever returns a stringly-typed "false"/"true", coercing it with plain
    bool() would silently flip the verdict. This is the strict parser used
    everywhere a validator's true/false judgment feeds into money movement.
    """
    if isinstance(value, bool):
        return value
    raise gl.vm.UserError(
        f"LLM_ERROR: field '{field_name}' must be a JSON boolean, "
        f"got {type(value).__name__}: {value!r}"
    )


def _parse_json_object(raw: str) -> dict:
    """
    Defensive JSON parse for LLM output (build brief section 3.4): strip
    markdown fences, slice to the outermost braces, drop trailing commas.
    Raises gl.vm.UserError if the result is still unparsable - bare Python
    exceptions crash the GenVM WASM runtime silently, per genvm-lint W004.
    """
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        raise gl.vm.UserError("LLM_ERROR: no JSON object found in model output")
    cleaned = cleaned[first_brace : last_brace + 1]
    cleaned = re.sub(r",(?!\s*?[\{\[\"\'\w])", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise gl.vm.UserError(f"LLM_ERROR: malformed JSON from model: {exc}")


@allow_storage
@dataclass
class Warning:
    source_url: str
    quote_text: str
    category: str
    submitter: Address
    submitted_at: str  # ISO 8601


@allow_storage
@dataclass
class Prophecy:
    structured_claim: str
    evidentiary_standard: str
    resolution_window_start: str
    resolution_window_end: str


@allow_storage
@dataclass
class ResolutionResult:
    occurred: bool
    linked: bool
    rationale: str
    resolved_at: str


@allow_storage
@dataclass
class ProphecyRecord:
    status: str
    warning: Warning
    prophecy: Prophecy
    resolution: ResolutionResult
    prophet_cut_bps: u256
    total_coverage: u256
    total_liquidity: u256
    evidence_url: str  # persisted so an appeal review re-fetches the same evidence


class Cassandra(gl.Contract):
    """
    Single contract powering the whole CASSANDRA protocol. Every Prophecy
    lives as one entry in `prophecies`, keyed by a sequential id - there is
    no per-prophecy contract deployment, so all state, consensus, and
    payout logic for the entire protocol runs through this one deployed
    address (see CASSANDRA_Coding_Agent_Build_Brief.md for the product
    rationale; this file supersedes the brief's earlier factory+pool split).
    """

    prophecy_count: u256
    prophecies: TreeMap[u256, ProphecyRecord]
    # Composite string keys ("<prophecy_id>:<address_hex>") instead of nested
    # TreeMap[u256, TreeMap[Address, u256]] - nested generic storage types are
    # not demonstrated in any shipped reference contract, so this avoids an
    # unverified pattern.
    coverage_positions: TreeMap[str, u256]
    lp_positions: TreeMap[str, u256]
    # Ordered, unique participant lists per prophecy - needed at settle() time
    # to enumerate exactly who to pay, since TreeMap has no "keys with this
    # prefix" query.
    coverage_holders: TreeMap[u256, DynArray[Address]]
    lp_holders: TreeMap[u256, DynArray[Address]]
    pools_by_category: TreeMap[str, DynArray[u256]]

    def __init__(self) -> None:
        self.prophecy_count = u256(0)

    def _position_key(self, prophecy_id: int, address: Address) -> str:
        return f"{prophecy_id}:{address.as_hex}"

    def _require_prophecy(self, prophecy_id: int) -> ProphecyRecord:
        key = u256(prophecy_id)
        if key not in self.prophecies:
            raise gl.vm.UserError(f"EXPECTED: no prophecy with id {prophecy_id}")
        return self.prophecies[key]

    # ------------------------------------------------------------------
    # SEED - deterministic write, creates a new Prophecy record.
    # ------------------------------------------------------------------
    @gl.public.write
    def submit_warning(
        self,
        source_url: str,
        quote_text: str,
        category: str,
        prophet_cut_bps: int = 500,  # default 5%
    ) -> int:
        if not source_url or not quote_text or not category:
            raise gl.vm.UserError("EXPECTED: source_url, quote_text and category are required")
        if prophet_cut_bps < 0 or prophet_cut_bps > 2000:
            raise gl.vm.UserError("EXPECTED: prophet_cut_bps must be between 0 and 2000 (20%)")

        record = ProphecyRecord(
            status=STATUS_DRAFTING,
            warning=Warning(
                source_url=source_url.strip(),
                quote_text=quote_text.strip(),
                category=category.strip().lower(),
                submitter=gl.message.sender_address,
                submitted_at=_now_iso(),
            ),
            prophecy=Prophecy(
                structured_claim="",
                evidentiary_standard="",
                resolution_window_start="",
                resolution_window_end="",
            ),
            resolution=ResolutionResult(occurred=False, linked=False, rationale="", resolved_at=""),
            prophet_cut_bps=u256(prophet_cut_bps),
            total_coverage=u256(0),
            total_liquidity=u256(0),
            evidence_url="",
        )

        prophecy_id = self.prophecy_count
        self.prophecies[prophecy_id] = record
        self.prophecy_count = u256(prophecy_id + 1)

        normalized_category = category.strip().lower()
        self.pools_by_category.get_or_insert_default(normalized_category).append(prophecy_id)

        return prophecy_id

    # ------------------------------------------------------------------
    # EXTRACTION - draft a falsifiable Prophecy claim from the raw Warning,
    # and VERIFY THE SOURCE first. Equivalence: custom validator
    # (prompt_non_comparative), NOT strict_eq. A leader-drafted claim will
    # never be byte-identical across validators; what must match is the
    # substantive event class, evidentiary bar and rough timeframe (build
    # brief section 3.3). Reaching eq_principle consensus on this write IS
    # the ratification step - no separate ratify_prophecy call is needed.
    #
    # Source verification: the leader fetches source_url and the model must
    # confirm warning_quote is genuinely supported by that content before
    # any claim is drafted - previously source_url was never fetched at all,
    # so a fabricated or dead source could be ratified and go on to accept
    # real GEN. If verification fails, this raises and the prophecy stays in
    # DRAFTING permanently (no state is written, no funds are ever at risk).
    # ------------------------------------------------------------------
    @gl.public.write
    def draft_prophecy(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_DRAFTING:
            raise gl.vm.UserError("EXPECTED: prophecy is not in DRAFTING status")

        quote_text = record.warning.quote_text
        category = record.warning.category
        source_url = record.warning.source_url
        evidentiary_guidance = CATEGORY_EVIDENTIARY_GUIDANCE.get(
            category, DEFAULT_EVIDENTIARY_GUIDANCE
        )

        def get_input() -> str:
            try:
                source_content = gl.nondet.web.render(source_url, mode="text")
            except Exception as exc:
                raise gl.vm.UserError(f"EXTERNAL: could not fetch source_url: {exc}")
            return f"""
<source_url>
{source_url}
</source_url>

<source_content>
{source_content}
</source_content>

<category>
{category}
</category>

<category_evidentiary_guidance>
{evidentiary_guidance}
</category_evidentiary_guidance>

<warning_quote>
{quote_text}
</warning_quote>
"""

        task = """
Draft a structured, falsifiable insurance claim from the public warning above -
but first, verify its source.

Step 1 - VERIFY: does source_content genuinely contain or substantively
support warning_quote (the same claim in substance, not necessarily verbatim)?
If source_content is empty, unreachable-looking, unrelated to warning_quote,
or contradicts it, the warning cannot be drafted - set source_verified to
false and fill the remaining fields with reasonable placeholders (they will
be ignored).

Step 2 - if verified, describe the specific event class this warning
predicts, the evidentiary bar needed to confirm it occurred, and a reasonable
resolution window (ISO 8601 start/end dates, window length appropriate to the
category - days for security exploits, months for climate/regulatory).

The evidentiary_standard you draft must follow the category_evidentiary_guidance
provided above - it sets the kind of source validators should require at
resolution time for this category, and should stay consistent across every
prophecy in the same category rather than being invented ad hoc.

Respond in strict JSON:
{
  "source_verified": true or false,
  "structured_claim": "one or two sentences, falsifiable, specific event class",
  "evidentiary_standard": "what kind of evidence would confirm this occurred",
  "resolution_window_start": "YYYY-MM-DD",
  "resolution_window_end": "YYYY-MM-DD"
}
It is mandatory that you respond only using the JSON format above, nothing else.
"""

        criteria = """
The output is valid JSON with exactly the five required keys. source_verified
is a boolean judging whether source_content genuinely supports warning_quote -
reject only if this judgment is clearly wrong given source_content (e.g. it
obviously contradicts or has nothing to do with warning_quote). If
source_verified is true: structured_claim names a specific, falsifiable event
class consistent with the warning_quote and category - it does not need to
match any particular wording. evidentiary_standard names a plausible kind of
evidence for that category. resolution_window_start and resolution_window_end
are both valid ISO 8601 dates, in order, with a length that is reasonable for
the category (days to weeks for security exploits, weeks to months for
climate/regulatory/systemic claims). Accept minor variation in exact wording
or exact dates - only reject if the claim is not falsifiable, not related to
the warning, or the JSON is malformed.
"""

        raw = gl.eq_principle.prompt_non_comparative(
            get_input,
            task=task,
            criteria=criteria,
        )
        parsed = _parse_json_object(raw)
        for key in (
            "source_verified",
            "structured_claim",
            "evidentiary_standard",
            "resolution_window_start",
            "resolution_window_end",
        ):
            if key not in parsed:
                raise gl.vm.UserError(f"LLM_ERROR: draft_prophecy missing field '{key}'")

        if not _strict_bool(parsed["source_verified"], "source_verified"):
            raise gl.vm.UserError(
                "EXPECTED: source_url does not verifiably support the submitted warning_quote"
            )
        for key in ("structured_claim", "evidentiary_standard", "resolution_window_start", "resolution_window_end"):
            if not isinstance(parsed[key], str) or not parsed[key]:
                raise gl.vm.UserError(f"LLM_ERROR: draft_prophecy invalid field '{key}'")

        # Build a brand-new ProphecyRecord and explicitly reassign it into the
        # TreeMap, rather than relying on in-place mutation of the object
        # returned by TreeMap.__getitem__ - this is the documented-safe write
        # pattern for storage-backed values in this SDK.
        new_record = ProphecyRecord(
            status=STATUS_RATIFIED,
            warning=record.warning,
            prophecy=Prophecy(
                structured_claim=parsed["structured_claim"],
                evidentiary_standard=parsed["evidentiary_standard"],
                resolution_window_start=parsed["resolution_window_start"],
                resolution_window_end=parsed["resolution_window_end"],
            ),
            resolution=record.resolution,
            prophet_cut_bps=record.prophet_cut_bps,
            total_coverage=record.total_coverage,
            total_liquidity=record.total_liquidity,
            evidence_url=record.evidence_url,
        )
        self.prophecies[u256(prophecy_id)] = new_record

    # ------------------------------------------------------------------
    # UNDERWRITE - deterministic, no equivalence principle needed. Both
    # methods are payable: the staked/premium amount is the real GEN sent
    # with the transaction (gl.message.value), not a caller-supplied int -
    # a plain int argument would let anyone claim to have staked/paid any
    # amount they like without actually sending it.
    # ------------------------------------------------------------------
    @gl.public.write.payable
    def provide_liquidity(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status not in (STATUS_RATIFIED, STATUS_UNDERWRITING, STATUS_ACTIVE):
            raise gl.vm.UserError("EXPECTED: pool is not accepting liquidity in its current status")
        amount = gl.message.value
        if amount <= u256(0):
            raise gl.vm.UserError("EXPECTED: must send GEN with this call")

        sender = gl.message.sender_address
        key = self._position_key(prophecy_id, sender)
        current = self.lp_positions.get(key, u256(0))
        if current == u256(0):
            self.lp_holders.get_or_insert_default(u256(prophecy_id)).append(sender)
        self.lp_positions[key] = u256(current + amount)
        record.total_liquidity = u256(record.total_liquidity + amount)

        if record.status == STATUS_RATIFIED:
            record.status = STATUS_UNDERWRITING
        self.prophecies[u256(prophecy_id)] = record

    @gl.public.write.payable
    def buy_coverage(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status not in (STATUS_UNDERWRITING, STATUS_ACTIVE):
            raise gl.vm.UserError("EXPECTED: pool is not selling coverage in its current status")
        amount = gl.message.value
        if amount <= u256(0):
            raise gl.vm.UserError("EXPECTED: must send GEN with this call")
        if record.total_coverage + amount > record.total_liquidity:
            raise gl.vm.UserError("EXPECTED: coverage requested exceeds underwritten liquidity")

        sender = gl.message.sender_address
        key = self._position_key(prophecy_id, sender)
        current = self.coverage_positions.get(key, u256(0))
        if current == u256(0):
            self.coverage_holders.get_or_insert_default(u256(prophecy_id)).append(sender)
        self.coverage_positions[key] = u256(current + amount)
        record.total_coverage = u256(record.total_coverage + amount)
        record.status = STATUS_ACTIVE
        self.prophecies[u256(prophecy_id)] = record

    # ------------------------------------------------------------------
    # OCCURRENCE + LINKAGE - the hardest non-determinism in the contract.
    # The leader fetches live web evidence and judges (a) did the event
    # class occur, and (b) is it substantively linked to the original
    # warning. Equivalence: prompt_non_comparative - the leader's fetched
    # evidence is the "input", and validators judge whether the leader's
    # occurred/linked conclusion is SUPPORTED BY that input, rather than
    # independently re-fetching and demanding byte-identical judgment.
    # This is deliberately not prompt_comparative: two independent web
    # fetches of a live page and two independent LLM judgments calls are
    # expected to diverge in wording even when they agree in substance,
    # and validators disagreeing on wording (not substance) must not block
    # consensus (verified empirically - prompt_comparative here produced
    # MAJORITY_DISAGREE/UNDETERMINED on StudioNet for this exact reason).
    #
    # Timing: resolution cannot be triggered before resolution_window_start
    # opens - this is checked deterministically, before any nondet call, so
    # it costs nothing to reject and never depends on model judgment. The
    # window bounds are also passed into the prompt so validators reject
    # stale/replayed evidence describing an event outside the warned window
    # (e.g. citing an older, unrelated incident to fraudulently claim a
    # newer prophecy) even though occurred/linked can't match exactly.
    # ------------------------------------------------------------------
    @gl.public.write
    def trigger_resolution(self, prophecy_id: int, evidence_url: str) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_ACTIVE:
            raise gl.vm.UserError("EXPECTED: pool is not ACTIVE, cannot resolve")
        if not evidence_url:
            raise gl.vm.UserError("EXPECTED: evidence_url is required")

        window_start_dt = _parse_iso_datetime(record.prophecy.resolution_window_start)
        if datetime.now(timezone.utc) < window_start_dt:
            raise gl.vm.UserError(
                f"EXPECTED: resolution window has not opened yet "
                f"(starts {record.prophecy.resolution_window_start})"
            )

        claim = record.prophecy.structured_claim
        standard = record.prophecy.evidentiary_standard
        original_quote = record.warning.quote_text
        window_start = record.prophecy.resolution_window_start
        window_end = record.prophecy.resolution_window_end

        def fetch_evidence() -> str:
            try:
                evidence_text = gl.nondet.web.render(evidence_url, mode="text")
            except Exception as exc:
                raise gl.vm.UserError(f"EXTERNAL: could not fetch evidence_url: {exc}")
            return f"""
<original_warning>
{original_quote}
</original_warning>

<structured_claim>
{claim}
</structured_claim>

<evidentiary_standard>
{standard}
</evidentiary_standard>

<resolution_window_start>
{window_start}
</resolution_window_start>

<resolution_window_end>
{window_end}
</resolution_window_end>

<evidence_url>
{evidence_url}
</evidence_url>

<evidence_content>
{evidence_text}
</evidence_content>
"""

        task = """
You are an AI validator resolving a parametric insurance claim about a warning
that may or may not have come true. Judge two separate questions:
1. occurred - did an event matching the structured_claim's event class actually
   happen, per the evidentiary_standard, based on the evidence_content, AND
   does its timing fall within the resolution window (resolution_window_start
   to resolution_window_end)? Evidence describing an event clearly outside
   that window - including reused evidence from an older, unrelated incident
   that happens to match the event class - does not satisfy this claim, even
   if the event class matches; treat it as not occurred within this window.
2. linked - if it occurred, is there a genuine causal or thematic link between
   the original_warning and what happened, as opposed to an unrelated coincidence?

Respond in strict JSON:
{
  "occurred": true or false,
  "linked": true or false,
  "rationale": "self-contained explanation a reader could verify independently"
}
It is mandatory that you respond only using the JSON format above, nothing else.
"""

        criteria = """
The output is valid JSON with exactly the three required keys, occurred and
linked are booleans, rationale is a non-empty string. The occurred/linked
conclusion is a reasonable, well-supported reading of the evidence_content
given the structured_claim, evidentiary_standard, and resolution window -
reject only if the conclusion contradicts the evidence_content, ignores the
evidentiary_standard, or ignores whether the evidenced event's timing falls
within the resolution window, not merely because the rationale is phrased
differently than you would phrase it.
"""

        raw = gl.eq_principle.prompt_non_comparative(
            fetch_evidence,
            task=task,
            criteria=criteria,
        )
        parsed = _parse_json_object(raw)
        for key in ("occurred", "linked", "rationale"):
            if key not in parsed:
                raise gl.vm.UserError(f"LLM_ERROR: trigger_resolution missing field '{key}'")

        record.resolution = ResolutionResult(
            occurred=_strict_bool(parsed["occurred"], "occurred"),
            linked=_strict_bool(parsed["linked"], "linked"),
            rationale=str(parsed["rationale"]),
            resolved_at=_now_iso(),
        )
        record.evidence_url = evidence_url
        record.status = STATUS_RESOLVING
        self.prophecies[u256(prophecy_id)] = record

    # ------------------------------------------------------------------
    # SETTLE - deterministic once ResolutionResult is finalized, but no
    # longer pure arithmetic: this is where real GEN actually moves, via
    # `_Recipient(addr).emit_transfer`. Shared by both the direct path
    # (settle(), from RESOLVING) and the post-appeal path
    # (finalize_appeal(), from DISPUTED) so a transfer only ever fires once
    # per prophecy, using whichever resolution is final at that point.
    #
    # Economics (design spec section 1.1/1.2 - LPs earn premium yield when
    # the warning is false, bear payout risk when it's true):
    #   Vindicated:     prophet gets prophet_cut_bps of total_coverage,
    #                   deducted from the coverage pool (not paid on top of
    #                   it) - each coverage holder gets their pro-rata share
    #                   of what's left, so prophet_share + sum(payouts) ==
    #                   total_coverage exactly (up to floor-division dust).
    #                   The earlier version paid the FULL total_coverage to
    #                   holders AND an extra prophet_share on top, which
    #                   over-paid beyond what buyers actually deposited -
    #                   the excess was quietly funded out of the LP-backed
    #                   liquidity pool with no accounting for it. LPs get
    #                   nothing further - their staked liquidity is the
    #                   capital that backed the claim, consumed by it.
    #   Not vindicated: no claim is paid. Each LP is repaid their principal
    #                   plus a pro-rata share of total_coverage (the
    #                   premiums) as yield. Coverage buyers get nothing
    #                   back - their premium was the cost of coverage that
    #                   didn't pay out.
    # All positions for this prophecy are zeroed after settlement (whether
    # paid or forfeited) so reads never show a stale balance for money that
    # has already moved or been consumed - this also fixes the frontend
    # Portfolio view continuing to show a position after settlement.
    # ------------------------------------------------------------------
    def _execute_settlement(self, prophecy_id: int, record: ProphecyRecord) -> None:
        vindicated = record.resolution.occurred and record.resolution.linked
        key = u256(prophecy_id)

        if vindicated:
            prophet_share = (record.total_coverage * record.prophet_cut_bps) // u256(10000)
            net_coverage_pool = u256(record.total_coverage - prophet_share)
            if prophet_share > u256(0):
                _Recipient(record.warning.submitter).emit_transfer(value=prophet_share)

            coverage_holder_count = 0
            paid_to_holders = u256(0)
            if key in self.coverage_holders and record.total_coverage > u256(0):
                for holder in self.coverage_holders[key]:
                    coverage_holder_count += 1
                    pos_key = self._position_key(prophecy_id, holder)
                    position = self.coverage_positions.get(pos_key, u256(0))
                    if position > u256(0):
                        payout = u256((position * net_coverage_pool) // record.total_coverage)
                        if payout > u256(0):
                            _Recipient(holder).emit_transfer(value=payout)
                            paid_to_holders = u256(paid_to_holders + payout)
                    self.coverage_positions[pos_key] = u256(0)

            if key in self.lp_holders:
                for holder in self.lp_holders[key]:
                    self.lp_positions[self._position_key(prophecy_id, holder)] = u256(0)

            record.resolution.rationale += (
                f" | SETTLED: vindicated, prophet_share={prophet_share} GEN paid, "
                f"{paid_to_holders} GEN paid across {coverage_holder_count} coverage holder(s)"
            )
        else:
            paid_to_lps = u256(0)
            lp_holder_count = 0
            if key in self.lp_holders and record.total_liquidity > u256(0):
                for holder in self.lp_holders[key]:
                    lp_holder_count += 1
                    pos_key = self._position_key(prophecy_id, holder)
                    principal = self.lp_positions.get(pos_key, u256(0))
                    if principal > u256(0):
                        yield_share = (principal * record.total_coverage) // record.total_liquidity
                        payout = u256(principal + yield_share)
                        _Recipient(holder).emit_transfer(value=payout)
                        paid_to_lps = u256(paid_to_lps + payout)
                    self.lp_positions[pos_key] = u256(0)

            if key in self.coverage_holders:
                for holder in self.coverage_holders[key]:
                    self.coverage_positions[self._position_key(prophecy_id, holder)] = u256(0)

            record.resolution.rationale += (
                f" | SETTLED: not vindicated, {paid_to_lps} GEN (principal + premium yield) "
                f"returned across {lp_holder_count} LP(s)"
            )

        record.status = STATUS_SETTLED
        self.prophecies[u256(prophecy_id)] = record

    @gl.public.write
    def settle(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_RESOLVING:
            raise gl.vm.UserError("EXPECTED: pool is not RESOLVING, cannot settle")
        self._execute_settlement(prophecy_id, record)

    # ------------------------------------------------------------------
    # APPEAL - authorized, validator-adjudicated, and always effective
    # before any transfer:
    #   - appeal() only accepts RESOLVING (never SETTLED) - once settle()
    #     has run, GEN has already moved and can't be clawed back on-chain,
    #     so an appeal must be raised before that point, not after.
    #   - appeal() requires standing: only the original warning submitter,
    #     a coverage holder, or an LP for this specific prophecy may appeal.
    #     Previously any address at all could dispute any prophecy.
    #   - finalize_appeal() no longer accepts a caller-supplied `upheld`
    #     bool - that let any single caller decide the outcome unilaterally
    #     with zero adjudication. It now re-fetches the same evidence and
    #     runs a fresh equivalence-principle judgment (occurred/linked),
    #     then immediately executes settlement from that corrected verdict
    #     - so the appeal's effect is baked into the resolution before the
    #     one and only transfer for this prophecy ever fires.
    # ------------------------------------------------------------------
    @gl.public.write
    def appeal(self, prophecy_id: int, reason: str) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_RESOLVING:
            raise gl.vm.UserError(
                "EXPECTED: prophecy must be RESOLVING (before settlement) to be appealed"
            )
        if not reason:
            raise gl.vm.UserError("EXPECTED: reason is required")

        sender = gl.message.sender_address
        has_standing = (
            sender == record.warning.submitter
            or self.coverage_positions.get(self._position_key(prophecy_id, sender), u256(0)) > u256(0)
            or self.lp_positions.get(self._position_key(prophecy_id, sender), u256(0)) > u256(0)
        )
        if not has_standing:
            raise gl.vm.UserError(
                "EXPECTED: only the warning's submitter, a coverage holder, or an LP may appeal"
            )

        record.status = STATUS_DISPUTED
        record.resolution.rationale += f" | DISPUTED by {sender.as_hex}: {reason}"
        self.prophecies[u256(prophecy_id)] = record

    @gl.public.write
    def finalize_appeal(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_DISPUTED:
            raise gl.vm.UserError("EXPECTED: prophecy is not under DISPUTED status")
        if not record.evidence_url:
            raise gl.vm.UserError("EXPECTED: no evidence on record to re-adjudicate")

        claim = record.prophecy.structured_claim
        standard = record.prophecy.evidentiary_standard
        original_quote = record.warning.quote_text
        window_start = record.prophecy.resolution_window_start
        window_end = record.prophecy.resolution_window_end
        evidence_url = record.evidence_url
        original_occurred = record.resolution.occurred
        original_linked = record.resolution.linked

        def fetch_evidence() -> str:
            try:
                evidence_text = gl.nondet.web.render(evidence_url, mode="text")
            except Exception as exc:
                raise gl.vm.UserError(f"EXTERNAL: could not fetch evidence_url on appeal: {exc}")
            return f"""
<original_warning>
{original_quote}
</original_warning>

<structured_claim>
{claim}
</structured_claim>

<evidentiary_standard>
{standard}
</evidentiary_standard>

<resolution_window_start>
{window_start}
</resolution_window_start>

<resolution_window_end>
{window_end}
</resolution_window_end>

<evidence_url>
{evidence_url}
</evidence_url>

<evidence_content>
{evidence_text}
</evidence_content>

<original_ruling>
occurred={original_occurred}, linked={original_linked}
</original_ruling>
"""

        task = """
You are an AI validator conducting an APPEAL REVIEW of a disputed parametric
insurance resolution - a fresh, independent re-examination with higher
scrutiny than the original resolution. Judge the same two questions again,
from evidence_content alone - do not defer to original_ruling, which may be
wrong; that is the entire point of the appeal:
1. occurred - did an event matching the structured_claim's event class
   actually happen, per the evidentiary_standard, based on evidence_content,
   and does its timing fall within the resolution window
   (resolution_window_start to resolution_window_end)?
2. linked - if it occurred, is there a genuine causal or thematic link
   between the original_warning and what happened?

Respond in strict JSON:
{
  "occurred": true or false,
  "linked": true or false,
  "rationale": "self-contained explanation a reader could verify independently"
}
It is mandatory that you respond only using the JSON format above, nothing else.
"""

        criteria = """
The output is valid JSON with exactly the three required keys, occurred and
linked are booleans, rationale is a non-empty string. The occurred/linked
conclusion is a reasonable, well-supported reading of evidence_content given
the structured_claim, evidentiary_standard, and resolution window - reject
only if the conclusion contradicts evidence_content, ignores the
evidentiary_standard, or ignores whether the evidenced event's timing falls
within the resolution window.
"""

        raw = gl.eq_principle.prompt_non_comparative(
            fetch_evidence,
            task=task,
            criteria=criteria,
        )
        parsed = _parse_json_object(raw)
        for key in ("occurred", "linked", "rationale"):
            if key not in parsed:
                raise gl.vm.UserError(f"LLM_ERROR: finalize_appeal missing field '{key}'")

        record.resolution = ResolutionResult(
            occurred=_strict_bool(parsed["occurred"], "occurred"),
            linked=_strict_bool(parsed["linked"], "linked"),
            rationale=record.resolution.rationale + " | APPEAL_REVIEW: " + str(parsed["rationale"]),
            resolved_at=_now_iso(),
        )
        # The appeal review is final - settle immediately from this
        # corrected verdict so no further appeal, and no second transfer,
        # is ever possible for this prophecy.
        self._execute_settlement(prophecy_id, record)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    @gl.public.view
    def get_prophecy_count(self) -> int:
        return self.prophecy_count

    @gl.public.view
    def get_prophecy_state(self, prophecy_id: int) -> dict:
        record = self._require_prophecy(prophecy_id)
        return {
            "status": record.status,
            "warning": {
                "source_url": record.warning.source_url,
                "quote_text": record.warning.quote_text,
                "category": record.warning.category,
                "submitter": record.warning.submitter.as_hex,
                "submitted_at": record.warning.submitted_at,
            },
            "prophecy": {
                "structured_claim": record.prophecy.structured_claim,
                "evidentiary_standard": record.prophecy.evidentiary_standard,
                "resolution_window_start": record.prophecy.resolution_window_start,
                "resolution_window_end": record.prophecy.resolution_window_end,
            },
            "total_coverage": record.total_coverage,
            "total_liquidity": record.total_liquidity,
            "prophet_cut_bps": record.prophet_cut_bps,
        }

    @gl.public.view
    def get_resolution_rationale(self, prophecy_id: int) -> str:
        # Must always be populated on any resolved state - this is CASSANDRA's
        # trust mechanism (design spec section 4.5); never truncate or hide it.
        record = self._require_prophecy(prophecy_id)
        if record.status in (STATUS_DRAFTING, STATUS_RATIFIED, STATUS_UNDERWRITING, STATUS_ACTIVE):
            return ""
        return record.resolution.rationale

    @gl.public.view
    def get_coverage_of(self, prophecy_id: int, address: str) -> int:
        return self.coverage_positions.get(self._position_key(prophecy_id, Address(address)), 0)

    @gl.public.view
    def get_liquidity_of(self, prophecy_id: int, address: str) -> int:
        return self.lp_positions.get(self._position_key(prophecy_id, Address(address)), 0)

    @gl.public.view
    def get_prophecies_by_category(self, category: str) -> list[int]:
        normalized = category.strip().lower()
        if normalized not in self.pools_by_category:
            return []
        return list(self.pools_by_category[normalized])
