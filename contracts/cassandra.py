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
STATUS_FINAL = "FINAL"

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
        )

        prophecy_id = self.prophecy_count
        self.prophecies[prophecy_id] = record
        self.prophecy_count = u256(prophecy_id + 1)

        normalized_category = category.strip().lower()
        self.pools_by_category.get_or_insert_default(normalized_category).append(prophecy_id)

        return prophecy_id

    # ------------------------------------------------------------------
    # EXTRACTION - draft a falsifiable Prophecy claim from the raw Warning.
    # Equivalence: custom validator (prompt_comparative), NOT strict_eq.
    # A leader-drafted claim will never be byte-identical across validators;
    # what must match is the substantive event class, evidentiary bar and
    # rough timeframe (build brief section 3.3). Reaching eq_principle
    # consensus on this write IS the ratification step - no separate
    # ratify_prophecy call is needed.
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

        input_text = f"""
<source_url>
{source_url}
</source_url>

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
Draft a structured, falsifiable insurance claim from the public warning above.
Describe the specific event class this warning predicts, the evidentiary bar
needed to confirm it occurred, and a reasonable resolution window (ISO 8601
start/end dates, window length appropriate to the category - days for
security exploits, months for climate/regulatory).

The evidentiary_standard you draft must follow the category_evidentiary_guidance
provided above - it sets the kind of source validators should require at
resolution time for this category, and should stay consistent across every
prophecy in the same category rather than being invented ad hoc.

Respond in strict JSON:
{
  "structured_claim": "one or two sentences, falsifiable, specific event class",
  "evidentiary_standard": "what kind of evidence would confirm this occurred",
  "resolution_window_start": "YYYY-MM-DD",
  "resolution_window_end": "YYYY-MM-DD"
}
It is mandatory that you respond only using the JSON format above, nothing else.
"""

        criteria = """
The output is valid JSON with exactly the four required keys.
structured_claim names a specific, falsifiable event class consistent with the
warning_quote and category - it does not need to match any particular wording.
evidentiary_standard names a plausible kind of evidence for that category.
resolution_window_start and resolution_window_end are both valid ISO 8601 dates,
in order, with a length that is reasonable for the category (days to weeks for
security exploits, weeks to months for climate/regulatory/systemic claims).
Accept minor variation in exact wording or exact dates - only reject if the
claim is not falsifiable, not related to the warning, or the JSON is malformed.
"""

        def get_input() -> str:
            return input_text

        raw = gl.eq_principle.prompt_non_comparative(
            get_input,
            task=task,
            criteria=criteria,
        )
        parsed = _parse_json_object(raw)
        for key in (
            "structured_claim",
            "evidentiary_standard",
            "resolution_window_start",
            "resolution_window_end",
        ):
            if key not in parsed or not isinstance(parsed[key], str) or not parsed[key]:
                raise gl.vm.UserError(f"LLM_ERROR: draft_prophecy missing/invalid field '{key}'")

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
        print("DEBUG provide_liquidity: done")

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
    # ------------------------------------------------------------------
    @gl.public.write
    def trigger_resolution(self, prophecy_id: int, evidence_url: str) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_ACTIVE:
            raise gl.vm.UserError("EXPECTED: pool is not ACTIVE, cannot resolve")
        if not evidence_url:
            raise gl.vm.UserError("EXPECTED: evidence_url is required")

        claim = record.prophecy.structured_claim
        standard = record.prophecy.evidentiary_standard
        original_quote = record.warning.quote_text
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
   happen, per the evidentiary_standard, based on the evidence_content?
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
given the structured_claim and evidentiary_standard - reject only if the
conclusion contradicts the evidence_content or ignores the evidentiary_standard,
not merely because the rationale is phrased differently than you would phrase it.
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
            occurred=bool(parsed["occurred"]),
            linked=bool(parsed["linked"]),
            rationale=str(parsed["rationale"]),
            resolved_at=_now_iso(),
        )
        record.status = STATUS_RESOLVING
        self.prophecies[u256(prophecy_id)] = record

    # ------------------------------------------------------------------
    # SETTLE - deterministic once ResolutionResult is finalized (no further
    # non-determinism at this point), but no longer pure arithmetic: this
    # is where real GEN actually moves, via `_Recipient(addr).emit_transfer`.
    #
    # Economics (design spec section 1.1/1.2 - LPs earn premium yield when
    # the warning is false, bear payout risk when it's true):
    #   Vindicated:     prophet gets prophet_cut_bps of total_coverage;
    #                   each coverage holder is paid their full coverage
    #                   amount, funded from the combined pool. LPs receive
    #                   nothing further - their staked liquidity is what
    #                   backed the claim. (total_coverage <= total_liquidity
    #                   is enforced at buy_coverage time, so this payout can
    #                   never exceed total_liquidity + total_coverage.)
    #   Not vindicated: no claim is paid. Each LP is repaid their principal
    #                   plus a pro-rata share of total_coverage (the
    #                   premiums) as yield. Coverage buyers get nothing
    #                   back - their premium was the cost of coverage that
    #                   didn't pay out.
    # ------------------------------------------------------------------
    @gl.public.write
    def settle(self, prophecy_id: int) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_RESOLVING:
            raise gl.vm.UserError("EXPECTED: pool is not RESOLVING, cannot settle")

        vindicated = record.resolution.occurred and record.resolution.linked
        key = u256(prophecy_id)

        if vindicated:
            prophet_share = (record.total_coverage * record.prophet_cut_bps) // u256(10000)
            if prophet_share > u256(0):
                _Recipient(record.warning.submitter).emit_transfer(value=prophet_share)

            coverage_holder_count = 0
            if key in self.coverage_holders:
                for holder in self.coverage_holders[key]:
                    coverage_holder_count += 1
                    payout = self.coverage_positions.get(
                        self._position_key(prophecy_id, holder), u256(0)
                    )
                    if payout > u256(0):
                        _Recipient(holder).emit_transfer(value=payout)

            record.resolution.rationale += (
                f" | SETTLED: vindicated, prophet_share={prophet_share} GEN paid, "
                f"{record.total_coverage} GEN paid across {coverage_holder_count} coverage holder(s)"
            )
        else:
            paid_to_lps = u256(0)
            lp_holder_count = 0
            if key in self.lp_holders and record.total_liquidity > u256(0):
                for holder in self.lp_holders[key]:
                    lp_holder_count += 1
                    principal = self.lp_positions.get(
                        self._position_key(prophecy_id, holder), u256(0)
                    )
                    if principal == u256(0):
                        continue
                    yield_share = (principal * record.total_coverage) // record.total_liquidity
                    payout = u256(principal + yield_share)
                    _Recipient(holder).emit_transfer(value=payout)
                    paid_to_lps = u256(paid_to_lps + payout)

            record.resolution.rationale += (
                f" | SETTLED: not vindicated, {paid_to_lps} GEN (principal + premium yield) "
                f"returned across {lp_holder_count} LP(s)"
            )

        record.status = STATUS_SETTLED
        self.prophecies[u256(prophecy_id)] = record

    # ------------------------------------------------------------------
    # APPEAL - marks a resolution as disputed. The larger-validator-set
    # re-run is invoked at the transaction/consensus layer via
    # `genlayer appeal <txId>`, not in-contract.
    # ------------------------------------------------------------------
    @gl.public.write
    def appeal(self, prophecy_id: int, reason: str) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status not in (STATUS_RESOLVING, STATUS_SETTLED):
            raise gl.vm.UserError("EXPECTED: nothing to appeal in current status")
        if not reason:
            raise gl.vm.UserError("EXPECTED: reason is required")
        record.status = STATUS_DISPUTED
        record.resolution.rationale += f" | DISPUTED: {reason}"
        self.prophecies[u256(prophecy_id)] = record

    @gl.public.write
    def finalize_appeal(self, prophecy_id: int, upheld: bool) -> None:
        record = self._require_prophecy(prophecy_id)
        if record.status != STATUS_DISPUTED:
            raise gl.vm.UserError("EXPECTED: prophecy is not under DISPUTED status")
        record.status = STATUS_SETTLED if upheld else STATUS_FINAL
        record.resolution.rationale += f" | APPEAL_RESOLVED: upheld={upheld}"
        self.prophecies[u256(prophecy_id)] = record

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
