"""
Five real end-to-end lifecycle runs against live StudioNet consensus,
covering the verdict space the contract supports:

1. Security warning resolved against real, detailed incident evidence
   (Ronin Network bridge validator-compromise hack) - testing whether
   validators correctly vindicate a genuinely well-documented match.
2. Security warning resolved against irrelevant evidence - not vindicated.
3. Climate warning resolved against a real, detailed drought event page -
   testing vindication in the climate category's stricter evidentiary bar.
4. Climate warning resolved against irrelevant evidence - not vindicated.
5. A resolved prophecy taken through appeal() -> finalize_appeal(), which
   now re-adjudicates (rather than accepting a caller-supplied verdict) and
   settles directly from the review's outcome - exercising the DISPUTED
   branch and the appeal-before-settlement ordering.

These are exploratory - the point is observing what validators genuinely
decide given real sources, not forcing a predetermined verdict.

Source URLs used for _seed_and_draft must genuinely contain/support the
quoted warning text - draft_prophecy now fetches source_url and requires
the model to verify this before drafting, so placeholder domains like
example.com will be rejected (this is the fix for "verify the original
warning source" from the review).

All five run against ONE shared deployed contract (module-scoped fixture)
rather than five separate deployments - StudioNet's public RPC enforces a
30 requests/minute rate limit, and five back-to-back deployments blew
through it immediately. A short pause between tests keeps each test's own
burst of calls (submit, draft, underwrite, cover, resolve, settle - each
polling for a receipt) under that ceiling too.
"""

import time

import pytest
from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

accounts = get_accounts()
FINALIZED = TransactionStatus.FINALIZED


@pytest.fixture(scope="module")
def contract():
    factory = get_contract_factory("Cassandra")
    return factory.deploy()


def _seed_and_draft(contract, source_url, quote, category):
    r = contract.submit_warning(args=[source_url, quote, category, 500]).transact()
    assert tx_execution_succeeded(r)
    prophecy_id = contract.get_prophecy_count(args=[]).call() - 1
    r = contract.draft_prophecy(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)
    return prophecy_id


def _underwrite_and_cover(contract, prophecy_id):
    lp = contract.connect(accounts[1])
    r = lp.provide_liquidity(args=[prophecy_id]).transact(
        value=10**16, wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)
    buyer = contract.connect(accounts[2])
    r = buyer.buy_coverage(args=[prophecy_id]).transact(
        value=5 * 10**15, wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)


def _resolve_and_settle(contract, prophecy_id, evidence_url):
    r = contract.trigger_resolution(args=[prophecy_id, evidence_url]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)
    r = contract.settle(args=[prophecy_id]).transact(wait_transaction_status=FINALIZED)
    assert tx_execution_succeeded(r)
    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    rationale = contract.get_resolution_rationale(args=[prophecy_id]).call()
    print(f"[{prophecy_id}] status={state['status']}")
    print(f"[{prophecy_id}] rationale={rationale}")
    return state, rationale


def test_verdict_1_security_real_evidence(contract):
    prophecy_id = _seed_and_draft(
        contract,
        "https://rekt.news/ronin-rekt/",
        "Ronin Network's bridge relied on only 5 of 9 validator signatures to "
        "authorize withdrawals, allowing an attacker who compromised 5 keys "
        "to drain 173,600 ETH and 25.5M USDC undetected for six days.",
        "security",
    )
    _underwrite_and_cover(contract, prophecy_id)
    state, rationale = _resolve_and_settle(
        contract, prophecy_id, "https://en.wikipedia.org/wiki/Ronin_Network"
    )
    print(f"VERDICT 1 (security, real evidence): {state['status']} | vindicated={'vindicated,' in rationale}")
    time.sleep(20)


def test_verdict_2_security_irrelevant_evidence(contract):
    prophecy_id = _seed_and_draft(
        contract,
        "https://rekt.news/ronin-rekt/",
        "The bridge multisig threshold is a single compromised signer away "
        "from total fund loss.",
        "security",
    )
    _underwrite_and_cover(contract, prophecy_id)
    state, rationale = _resolve_and_settle(
        contract, prophecy_id, "https://en.wikipedia.org/wiki/Special:Random"
    )
    print(f"VERDICT 2 (security, irrelevant evidence): {state['status']} | vindicated={'vindicated,' in rationale}")
    time.sleep(20)


def test_verdict_3_climate_real_evidence(contract):
    prophecy_id = _seed_and_draft(
        contract,
        "https://reliefweb.int/report/ethiopia/horn-africa-drought-crisis-2022",
        "Sustained below-average rainfall across the Horn of Africa over "
        "four consecutive rainy seasons has driven the region into its "
        "worst drought in 40 years, with over 36 million people facing "
        "acute food insecurity across Ethiopia, Kenya, and Somalia.",
        "climate",
    )
    _underwrite_and_cover(contract, prophecy_id)
    state, rationale = _resolve_and_settle(
        contract, prophecy_id, "https://en.wikipedia.org/wiki/2020%E2%80%932023_Horn_of_Africa_drought"
    )
    print(f"VERDICT 3 (climate, real evidence): {state['status']} | vindicated={'vindicated,' in rationale}")
    time.sleep(20)


def test_verdict_4_climate_irrelevant_evidence(contract):
    prophecy_id = _seed_and_draft(
        contract,
        "https://reliefweb.int/report/ethiopia/horn-africa-drought-crisis-2022",
        "Rainfall in the Sahel basin has dropped below historical "
        "minimums for the third consecutive month.",
        "climate",
    )
    _underwrite_and_cover(contract, prophecy_id)
    state, rationale = _resolve_and_settle(
        contract, prophecy_id, "https://en.wikipedia.org/wiki/Special:Random"
    )
    print(f"VERDICT 4 (climate, irrelevant evidence): {state['status']} | vindicated={'vindicated,' in rationale}")
    time.sleep(20)


def test_verdict_5_appeal_flow(contract):
    """
    Appeals must now be raised before settle() runs (RESOLVING, not
    SETTLED) and finalize_appeal() re-adjudicates and settles directly -
    there is no separate caller-supplied verdict step anymore.
    """
    prophecy_id = _seed_and_draft(
        contract,
        "https://rekt.news/ronin-rekt/",
        "A protocol's bridge validator set can be compromised via a small "
        "number of leaked signing keys, allowing forged withdrawal approvals.",
        "security",
    )
    _underwrite_and_cover(contract, prophecy_id)

    r = contract.trigger_resolution(
        args=[prophecy_id, "https://en.wikipedia.org/wiki/Special:Random"]
    ).transact(wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED)
    assert tx_execution_succeeded(r)

    resolving_state = contract.get_prophecy_state(args=[prophecy_id]).call()
    print(f"VERDICT 5 after trigger_resolution: status={resolving_state['status']}")
    assert resolving_state["status"] == "RESOLVING"

    # Appeal from the original submitter (has standing) while still RESOLVING,
    # i.e. before any transfer has happened for this prophecy.
    r = contract.appeal(args=[prophecy_id, "Disputing the resolution for test purposes"]).transact(
        wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)
    disputed_state = contract.get_prophecy_state(args=[prophecy_id]).call()
    print(f"VERDICT 5 after appeal(): status={disputed_state['status']}")
    assert disputed_state["status"] == "DISPUTED"

    # finalize_appeal takes no caller-supplied verdict - it re-adjudicates
    # against the same stored evidence_url and settles from that outcome.
    r = contract.finalize_appeal(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    assert tx_execution_succeeded(r)
    final_state = contract.get_prophecy_state(args=[prophecy_id]).call()
    final_rationale = contract.get_resolution_rationale(args=[prophecy_id]).call()
    print(f"VERDICT 5 (post-appeal-review): status={final_state['status']}")
    print(f"VERDICT 5 rationale: {final_rationale}")
    assert final_state["status"] == "SETTLED"
    assert "APPEAL_REVIEW" in final_rationale
    assert "SETTLED" in final_rationale

    # Appeal is no longer possible once settled - transfers already fired.
    r = contract.appeal(args=[prophecy_id, "too late"]).transact()
    assert not tx_execution_succeeded(r)
