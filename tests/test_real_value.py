"""
Real GEN movement test: @gl.public.write.payable methods must actually
receive gl.message.value, not just accept a caller-supplied int claim.
Separate from tests/test_cassandra.py because it's slower (LLM draft step
required before underwriting is allowed).
"""

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

accounts = get_accounts()


def test_provide_liquidity_moves_real_gen():
    factory = get_contract_factory("Cassandra")
    contract = factory.deploy()

    submit_result = contract.submit_warning(
        args=[
            "https://example.com/real-value-test",
            "Testing that provide_liquidity actually receives GEN.",
            "security",
            500,
        ]
    ).transact()
    assert tx_execution_succeeded(submit_result)
    prophecy_id = contract.get_prophecy_count(args=[]).call() - 1

    draft_result = contract.draft_prophecy(args=[prophecy_id]).transact(
        wait_interval=15000, wait_retries=20
    )
    assert tx_execution_succeeded(draft_result)

    lp_contract = contract.connect(accounts[1])
    lp_address = accounts[1].address

    stake_amount = 10**16  # 0.01 GEN in wei

    result = lp_contract.provide_liquidity(args=[prophecy_id]).transact(value=stake_amount)
    assert tx_execution_succeeded(result)

    on_chain_position = contract.get_liquidity_of(args=[prophecy_id, lp_address]).call()
    assert on_chain_position == stake_amount, "Recorded position does not match real value sent"

    state = contract.get_prophecy_state(args=[prophecy_id]).call()
    assert state["total_liquidity"] == stake_amount
    assert state["status"] == "UNDERWRITING"
