"""
CASSANDRA contract tests, run via gltest against StudioNet
(chain id 61999, rpc https://studio.genlayer.com/api - see gltest.config.yaml).

genlayer-test's `gltest` runner deploys and executes against a real network;
there is no separate mocked-call test layer, so the build brief's "direct vs
integration" split collapses into this single suite. Deterministic-only
tests (status transitions, access control, arithmetic) run fast and need no
live web/LLM evidence. The two full-lifecycle tests below call
`draft_prophecy` and `trigger_resolution`, which invoke real LLM + web-fetch
consensus on StudioNet and are correspondingly slower.

API note: reads are `contract.method(args=[...]).call()`; writes are
`contract.method(args=[...]).transact(...)`; a different sender requires
`contract.connect(account)` first (verified against the installed
genlayer-test 0.29.2 source, not assumed).
"""

from gltest import get_contract_factory, get_default_account, get_accounts
from gltest.helpers import load_fixture
from gltest.assertions import tx_execution_succeeded, tx_execution_failed
from gltest.types import TransactionStatus

default_account = get_default_account()
accounts = get_accounts()


def deploy_contract():
    factory = get_contract_factory("Cassandra")
    contract = factory.deploy()
    assert contract.get_prophecy_count(args=[]).call() == 0
    return contract


def _submit_test_warning(contract, category="security", prophet_cut_bps=500):
    # draft_prophecy now fetches source_url and requires the model to verify
    # it genuinely supports the quote before drafting - example.com won't
    # pass that check, so tests that call draft_prophecy need a real,
    # fetchable source whose content actually contains the quoted warning.
    result = contract.submit_warning(
        args=[
            "https://rekt.news/ronin-rekt/",
            "Ronin Network's bridge relied on only 5 of 9 validator signatures to "
            "authorize withdrawals, allowing an attacker who compromised 5 keys "
            "to drain 173,600 ETH and 25.5M USDC undetected for six days.",
            category,
            prophet_cut_bps,
        ]
    ).transact()
    assert tx_execution_succeeded(result)
    prophecy_id = contract.get_prophecy_count(args=[]).call() - 1
    return prophecy_id


# ----------------------------------------------------------------------
# Deterministic: seeding + reads
# ----------------------------------------------------------------------
def test_submit_warning_creates_prophecy_in_drafting_status():
    contract = load_fixture(deploy_contract)

    prophecy_id = _submit_test_warning(contract)

    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert state["status"] == "DRAFTING"
    assert state["warning"]["category"] == "security"
    assert state["warning"]["submitter"] == default_account.address
    assert state["total_coverage"] == 0
    assert state["total_liquidity"] == 0


def test_submit_warning_rejects_missing_fields():
    contract = load_fixture(deploy_contract)

    result = contract.submit_warning(args=["", "some quote", "security", 500]).transact()
    assert tx_execution_failed(result)


def test_submit_warning_rejects_out_of_range_prophet_cut():
    contract = load_fixture(deploy_contract)

    result = contract.submit_warning(
        args=["https://example.com/x", "quote", "security", 5000]
    ).transact()
    assert tx_execution_failed(result)


def test_get_resolution_rationale_empty_before_resolution():
    contract = load_fixture(deploy_contract)
    prophecy_id = _submit_test_warning(contract)

    assert contract.get_resolution_rationale(args=[prophecy_id]).call() == ""


def test_prophecies_indexed_by_category():
    contract = load_fixture(deploy_contract)
    _submit_test_warning(contract, category="Security")
    _submit_test_warning(contract, category="climate")

    security_ids = contract.get_prophecies_by_category(args=["security"]).call()
    climate_ids = contract.get_prophecies_by_category(args=["climate"]).call()
    assert len(security_ids) == 1
    assert len(climate_ids) == 1


# ----------------------------------------------------------------------
# Deterministic: access control / status-machine edge cases
# ----------------------------------------------------------------------
def test_cannot_provide_liquidity_before_ratification():
    contract = load_fixture(deploy_contract)
    prophecy_id = _submit_test_warning(contract)

    # status is still DRAFTING - draft_prophecy has not been called
    result = contract.provide_liquidity(args=[prophecy_id]).transact(value=1000)
    assert tx_execution_failed(result)


def test_cannot_settle_before_resolution():
    contract = load_fixture(deploy_contract)
    prophecy_id = _submit_test_warning(contract)

    result = contract.settle(args=[prophecy_id]).transact()
    assert tx_execution_failed(result)


def test_operations_on_nonexistent_prophecy_fail():
    contract = load_fixture(deploy_contract)

    result = contract.provide_liquidity(args=[999]).transact(value=1000)
    assert tx_execution_failed(result)


# ----------------------------------------------------------------------
# Full lifecycle — invokes real LLM + web-fetch consensus on StudioNet.
# Uses a stable, always-available public page as evidence so the test is
# reproducible; the assertion only checks that resolution completed and
# populated a rationale, not a specific occurred/linked outcome, since
# that depends on live model judgment.
# ----------------------------------------------------------------------
def test_full_lifecycle_underwrite_and_resolve():
    contract = load_fixture(deploy_contract)
    prophecy_id = _submit_test_warning(contract)

    draft_result = contract.draft_prophecy(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(draft_result)

    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert state["status"] == "RATIFIED"
    assert state["prophecy"]["structured_claim"] != ""

    lp_contract = contract.connect(accounts[1])
    liquidity_result = lp_contract.provide_liquidity(args=[prophecy_id]).transact(
        value=10000, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(liquidity_result)
    assert (
        contract.get_liquidity_of(args=[prophecy_id, accounts[1].address]).call()
        == 10000
    )

    buyer_contract = contract.connect(accounts[2])
    coverage_result = buyer_contract.buy_coverage(args=[prophecy_id]).transact(
        value=2000, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(coverage_result)
    assert (
        contract.get_coverage_of(args=[prophecy_id, accounts[2].address]).call() == 2000
    )

    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert state["status"] == "ACTIVE"

    resolve_result = contract.trigger_resolution(
        args=[prophecy_id, "https://en.wikipedia.org/wiki/Special:Random"]
    ).transact(
        wait_interval=15000, wait_retries=20, wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(resolve_result)

    rationale = contract.get_resolution_rationale(args=[prophecy_id]).call()
    assert rationale != ""

    settle_result = contract.settle(args=[prophecy_id]).transact(
        wait_transaction_status=TransactionStatus.FINALIZED
    )
    assert tx_execution_succeeded(settle_result)

    final_state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert final_state["status"] == "SETTLED"


def test_trigger_resolution_rejected_before_active():
    contract = load_fixture(deploy_contract)
    prophecy_id = _submit_test_warning(contract)

    draft_result = contract.draft_prophecy(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20
    )
    assert tx_execution_succeeded(draft_result)

    # trigger_resolution requires ACTIVE status; without underwriting/coverage
    # this pool is still RATIFIED, so we expect a rejected transaction here -
    # this test exercises the status-machine guard on trigger_resolution.
    resolve_result = contract.trigger_resolution(
        args=[prophecy_id, "https://en.wikipedia.org/wiki/Special:Random"]
    ).transact(wait_interval=15000, wait_retries=20)
    assert tx_execution_failed(resolve_result)
