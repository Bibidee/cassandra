"""
ONE-OFF / MANUAL SCRIPT - not part of the automated regression suite.

Purpose: drives a full submit -> draft -> underwrite -> buy coverage ->
resolve -> settle lifecycle, plus a full appeal -> finalize_appeal cycle on
a second prophecy, against the fixed contract redeployed after the review
from Pavel Kolosov (2026-08-02) - CANONICAL_ADDRESS below. The previous
canonical contract (0xaa7F8f...) predates the value-conservation, window,
appeal-authorization, and source-verification fixes and was left as-is;
this script populates the NEW deployment so its transaction history is
visible end-to-end on the block explorer, matching what was done for the
original canonical deployment.

Uses real, fetchable source URLs (not example.com placeholders) since
draft_prophecy now verifies source_url genuinely supports the quoted
warning before drafting.

Written as a pytest test only because gltest's get_contract_factory()/
get_accounts() rely on pytest_configure hooks and won't initialize outside
a pytest session - it is not meant to be run routinely.
"""

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

CANONICAL_ADDRESS = "0x128A3ce1dfa92D15392E292Cd661B5680F08F31A"
FINALIZED = TransactionStatus.FINALIZED

accounts = get_accounts()


def test_run_new_canonical_lifecycle():
    factory = get_contract_factory("Cassandra")
    contract = factory.build_contract(contract_address=CANONICAL_ADDRESS)

    # ------------------------------------------------------------------
    # Prophecy 0: full lifecycle through direct settle() - real evidence,
    # exercising the fixed vindicated-payout math.
    # ------------------------------------------------------------------
    r = contract.submit_warning(
        args=[
            "https://rekt.news/ronin-rekt/",
            "Ronin Network's bridge relied on only 5 of 9 validator signatures to "
            "authorize withdrawals, allowing an attacker who compromised 5 keys to "
            "drain 173,600 ETH and 25.5M USDC undetected for six days.",
            "security",
            500,
        ]
    ).transact()
    print(f"submit_warning (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)
    prophecy_0 = contract.get_prophecy_count(args=[]).call() - 1

    r = contract.draft_prophecy(args=[prophecy_0]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    print(f"draft_prophecy (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    lp_contract = contract.connect(accounts[1])
    stake_amount = 2 * 10**16  # 0.02 GEN
    r = lp_contract.provide_liquidity(args=[prophecy_0]).transact(
        value=stake_amount, wait_transaction_status=FINALIZED
    )
    print(f"provide_liquidity (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    buyer_contract = contract.connect(accounts[2])
    coverage_amount = 10**16  # 0.01 GEN
    r = buyer_contract.buy_coverage(args=[prophecy_0]).transact(
        value=coverage_amount, wait_transaction_status=FINALIZED
    )
    print(f"buy_coverage (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.trigger_resolution(
        args=[prophecy_0, "https://en.wikipedia.org/wiki/Ronin_Network"]
    ).transact(wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED)
    print(f"trigger_resolution (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.settle(args=[prophecy_0]).transact(wait_transaction_status=FINALIZED)
    print(f"settle (0): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    state = contract.get_prophecy_state(args=[prophecy_0]).call()
    rationale = contract.get_resolution_rationale(args=[prophecy_0]).call()
    print(f"Prophecy 0 final status: {state['status']}")
    print(f"Prophecy 0 rationale: {rationale}")

    # ------------------------------------------------------------------
    # Prophecy 1: full lifecycle through appeal() -> finalize_appeal(),
    # exercising the re-adjudicated appeal path end to end.
    # ------------------------------------------------------------------
    r = contract.submit_warning(
        args=[
            "https://rekt.news/ronin-rekt/",
            "A protocol's bridge validator set can be compromised via a small "
            "number of leaked signing keys, allowing forged withdrawal approvals.",
            "security",
            500,
        ]
    ).transact()
    print(f"submit_warning (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)
    prophecy_1 = contract.get_prophecy_count(args=[]).call() - 1

    r = contract.draft_prophecy(args=[prophecy_1]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    print(f"draft_prophecy (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = lp_contract.provide_liquidity(args=[prophecy_1]).transact(
        value=stake_amount, wait_transaction_status=FINALIZED
    )
    print(f"provide_liquidity (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = buyer_contract.buy_coverage(args=[prophecy_1]).transact(
        value=coverage_amount, wait_transaction_status=FINALIZED
    )
    print(f"buy_coverage (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.trigger_resolution(
        args=[prophecy_1, "https://en.wikipedia.org/wiki/Special:Random"]
    ).transact(wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED)
    print(f"trigger_resolution (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.appeal(args=[prophecy_1, "Disputing this resolution for canonical demo purposes"]).transact(
        wait_transaction_status=FINALIZED
    )
    print(f"appeal (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    disputed_state = contract.get_prophecy_state(args=[prophecy_1]).call()
    print(f"Prophecy 1 status after appeal(): {disputed_state['status']}")
    assert disputed_state["status"] == "DISPUTED"

    r = contract.finalize_appeal(args=[prophecy_1]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=FINALIZED
    )
    print(f"finalize_appeal (1): {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    final_state = contract.get_prophecy_state(args=[prophecy_1]).call()
    final_rationale = contract.get_resolution_rationale(args=[prophecy_1]).call()
    print(f"Prophecy 1 final status: {final_state['status']}")
    print(f"Prophecy 1 rationale: {final_rationale}")

    print(f"\nFinal prophecy count on {CANONICAL_ADDRESS}: {contract.get_prophecy_count(args=[]).call()}")
