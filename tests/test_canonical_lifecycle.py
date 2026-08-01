"""
ONE-OFF / MANUAL SCRIPT - not part of the automated regression suite.

Purpose: drives the underwrite -> buy coverage -> resolve -> settle steps
against one specific, already-deployed contract address (CANONICAL_ADDRESS
below), rather than an ephemeral gltest fixture deployment. This was used
to make the full lifecycle visible on the GenLayer block explorer for the
canonical CASSANDRA StudioNet deployment, so the transaction history could
be inspected end-to-end for that exact address instead of a throwaway test
instance.

Written as a pytest test (not a bare script) only because gltest's
get_contract_factory()/get_accounts() rely on pytest_configure hooks and
won't initialize outside a pytest session - it is not meant to be run
routinely, and CANONICAL_ADDRESS will need updating (or the prophecy will
already be past DRAFTING) if run again after a redeploy.
"""

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus

CANONICAL_ADDRESS = "0xaa7F8f52228B6001DbC276397B4519F3EA05FFB0"
PROPHECY_ID = 0

accounts = get_accounts()


def test_run_canonical_lifecycle():
    factory = get_contract_factory("Cassandra")
    contract = factory.build_contract(contract_address=CANONICAL_ADDRESS)

    lp_contract = contract.connect(accounts[1])
    stake_amount = 2 * 10**16  # 0.02 GEN
    r = lp_contract.provide_liquidity(args=[PROPHECY_ID]).transact(
        value=stake_amount, wait_transaction_status=TransactionStatus.FINALIZED
    )
    print(f"provide_liquidity: {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    buyer_contract = contract.connect(accounts[2])
    coverage_amount = 10**16  # 0.01 GEN
    r = buyer_contract.buy_coverage(args=[PROPHECY_ID]).transact(
        value=coverage_amount, wait_transaction_status=TransactionStatus.FINALIZED
    )
    print(f"buy_coverage: {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.trigger_resolution(
        args=[PROPHECY_ID, "https://en.wikipedia.org/wiki/Special:Random"]
    ).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=TransactionStatus.FINALIZED
    )
    print(f"trigger_resolution: {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    r = contract.settle(args=[PROPHECY_ID]).transact(wait_transaction_status=TransactionStatus.FINALIZED)
    print(f"settle: {r['hash']} -> {tx_execution_succeeded(r)}")
    assert tx_execution_succeeded(r)

    state = contract.get_prophecy_state(args=[PROPHECY_ID]).call()
    rationale = contract.get_resolution_rationale(args=[PROPHECY_ID]).call()
    print(f"Final status: {state['status']}")
    print(f"Rationale: {rationale}")
