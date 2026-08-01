"""
Full lifecycle with real GEN movement: submit -> draft -> underwrite (real
stake) -> buy coverage (real premium) -> resolve -> settle (real payout).
Uses a genuinely relevant evidence URL to exercise the vindicated payout
path (prophet + coverage holder payouts), which test_cassandra.py's
lifecycle test does not cover (it deliberately uses a random/unrelated
evidence URL to test the not-vindicated path).
"""

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

accounts = get_accounts()


def test_full_lifecycle_with_real_gen_payout():
    factory = get_contract_factory("Cassandra")
    contract = factory.deploy()

    submit_result = contract.submit_warning(
        args=[
            "https://en.wikipedia.org/wiki/Sahel_drought",
            "Multiple consecutive months of rainfall in the Sahel region "
            "have fallen below the historical average, consistent with "
            "an ongoing extreme drought event.",
            "climate",
            500,
        ]
    ).transact()
    assert tx_execution_succeeded(submit_result)
    prophecy_id = contract.get_prophecy_count(args=[]).call() - 1

    draft_result = contract.draft_prophecy(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(draft_result)

    lp_contract = contract.connect(accounts[1])
    stake_amount = 2 * 10**16  # 0.02 GEN
    liquidity_result = lp_contract.provide_liquidity(args=[prophecy_id]).transact(
        value=stake_amount, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(liquidity_result)

    buyer_contract = contract.connect(accounts[2])
    coverage_amount = 10**16  # 0.01 GEN
    coverage_result = buyer_contract.buy_coverage(args=[prophecy_id]).transact(
        value=coverage_amount, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(coverage_result)

    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert state["status"] == "ACTIVE"
    assert state["total_coverage"] == coverage_amount
    assert state["total_liquidity"] == stake_amount

    resolve_result = contract.trigger_resolution(
        args=[prophecy_id, "https://en.wikipedia.org/wiki/Sahel_drought"]
    ).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(resolve_result)

    settle_result = contract.settle(args=[prophecy_id]).transact(
        wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(settle_result)

    final_state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert final_state["status"] == "SETTLED"

    rationale = contract.get_resolution_rationale(args=[prophecy_id]).call()
    print(f"Final rationale: {rationale}")
    assert "SETTLED" in rationale
