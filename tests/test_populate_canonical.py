"""
ONE-OFF / MANUAL SCRIPT - not part of the automated regression suite.

Populates the canonical StudioNet deployment with real activity: 2 rounds
across all 5 launch categories (10 full lifecycles total), each taken
through submit -> draft -> underwrite -> buy coverage -> resolve -> settle
against the exact CANONICAL_ADDRESS, so the contract's transaction history
on the block explorer reflects genuine, varied usage rather than a single
demo prophecy. Real evidence URLs are used for roughly half the scenarios
to get a natural mix of vindicated/not-vindicated outcomes rather than
forcing one; the rest use a random Wikipedia page as deliberately
irrelevant evidence.

Written as a pytest test for the same reason as test_canonical_lifecycle.py:
gltest's get_contract_factory()/get_accounts() need a pytest session.
Paced with short sleeps between rounds to stay under StudioNet's public
RPC rate limits (500 req/hour, 8 concurrent execution slots).
"""

import time

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

CANONICAL_ADDRESS = "0xaa7F8f52228B6001DbC276397B4519F3EA05FFB0"
FINALIZED = TransactionStatus.FINALIZED

accounts = get_accounts()

IRRELEVANT = "https://en.wikipedia.org/wiki/Special:Random"

SCENARIOS = [
    # Round 1
    dict(
        category="security",
        quote="A cross-chain bridge's cross-chain messaging protocol trusts a small "
        "set of off-chain relayers to attest to deposits without independent "
        "on-chain verification, allowing a compromised relayer to fabricate deposits.",
        evidence="https://en.wikipedia.org/wiki/Poly_Network_exploit",
    ),
    dict(
        category="climate",
        quote="Localized rainfall this month has been below seasonal norms.",
        evidence=IRRELEVANT,
    ),
    dict(
        category="depeg",
        quote="An algorithmic stablecoin's peg mechanism depends on a companion "
        "volatile token absorbing demand shocks; if confidence collapses, the "
        "arbitrage loop can spiral instead of correcting the peg.",
        evidence="https://en.wikipedia.org/wiki/Terra_(blockchain)",
    ),
    dict(
        category="regulatory",
        quote="A major exchange is operating in a jurisdiction without the "
        "required securities registrations for the tokens it lists.",
        evidence="https://en.wikipedia.org/wiki/Ripple_Labs",
    ),
    dict(
        category="systemic",
        quote="A large market maker's balance sheet is rumored to be overleveraged "
        "against illiquid collateral.",
        evidence=IRRELEVANT,
    ),
    # Round 2
    dict(
        category="security",
        quote="A protocol's admin key is held by a single EOA rather than a "
        "timelocked multisig, allowing a single compromised key to drain funds.",
        evidence=IRRELEVANT,
    ),
    dict(
        category="climate",
        quote="Multi-year rainfall deficits in a major agricultural region are "
        "consistent with the onset of a severe drought.",
        evidence="https://en.wikipedia.org/wiki/2011%E2%80%9317_California_drought",
    ),
    dict(
        category="depeg",
        quote="A stablecoin's reserve attestations have not been published in "
        "several months, raising doubts about full backing.",
        evidence=IRRELEVANT,
    ),
    dict(
        category="regulatory",
        quote="A central bank is considering a blanket ban on retail access to "
        "crypto exchanges.",
        evidence=IRRELEVANT,
    ),
    dict(
        category="systemic",
        quote="A major stablecoin depeg could cascade into forced liquidations "
        "across several large lending protocols and funds that hold it as collateral.",
        evidence="https://en.wikipedia.org/wiki/2022_cryptocurrency_bear_market",
    ),
]


def test_populate_canonical_with_two_rounds_of_every_category():
    factory = get_contract_factory("Cassandra")
    contract = factory.build_contract(contract_address=CANONICAL_ADDRESS)

    for i, scenario in enumerate(SCENARIOS):
        category = scenario["category"]
        print(f"\n=== Scenario {i}: {category} ===")

        r = contract.submit_warning(
            args=[f"https://example.com/warning-{i}", scenario["quote"], category, 500]
        ).transact()
        assert tx_execution_succeeded(r), f"submit_warning failed for scenario {i}"
        prophecy_id = contract.get_prophecy_count(args=[]).call() - 1

        r = contract.draft_prophecy(args=[prophecy_id]).transact(
            wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
        )
        assert tx_execution_succeeded(r), f"draft_prophecy failed for scenario {i}"

        lp = contract.connect(accounts[1])
        r = lp.provide_liquidity(args=[prophecy_id]).transact(
            value=10**16, wait_transaction_status=FINALIZED
        )
        assert tx_execution_succeeded(r), f"provide_liquidity failed for scenario {i}"

        buyer = contract.connect(accounts[2])
        r = buyer.buy_coverage(args=[prophecy_id]).transact(
            value=5 * 10**15, wait_transaction_status=FINALIZED
        )
        assert tx_execution_succeeded(r), f"buy_coverage failed for scenario {i}"

        r = contract.trigger_resolution(args=[prophecy_id, scenario["evidence"]]).transact(
            wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
        )
        assert tx_execution_succeeded(r), f"trigger_resolution failed for scenario {i}"

        r = contract.settle(args=[prophecy_id]).transact(wait_transaction_status=FINALIZED)
        assert tx_execution_succeeded(r), f"settle failed for scenario {i}"

        state = contract.get_prophecy_state(args=[prophecy_id]).call()
        rationale = contract.get_resolution_rationale(args=[prophecy_id]).call()
        print(f"[{prophecy_id}] {category}: status={state['status']} vindicated={'vindicated,' in rationale}")

        time.sleep(15)

    final_count = contract.get_prophecy_count(args=[]).call()
    print(f"\nFinal prophecy count on canonical contract: {final_count}")
