# CASSANDRA

Parametric insurance that pays out when documented public warnings come true, adjudicated by GenLayer's AI-validator consensus rather than a single arbiter or price feed.

## Links

| | |
|---|---|
| GitHub | https://github.com/Bibidee/cassandra |
| Live app | https://the-cassandra.vercel.app |
| Contract explorer | https://explorer-studio.genlayer.com/address/0x128A3ce1dfa92D15392E292Cd661B5680F08F31A |
| Contract address | `0x128A3ce1dfa92D15392E292Cd661B5680F08F31A` |
| Network | GenLayer StudioNet (chain id 61999) |
| RPC | https://studio.genlayer.com/api |

## What it does

A prophet submits a public warning with a source URL and verbatim quote. GenLayer's validator network drafts it into a falsifiable claim with an evidentiary standard and resolution window. Liquidity providers underwrite the pool; buyers pay a premium for coverage. When evidence is submitted, validators independently fetch and read it, then judge two questions: did the event occur, and is it causally linked to the original warning? If they reach consensus that it was vindicated, coverage holders are paid out. If not, premiums are retained by liquidity providers as yield.

Every resolution rationale is stored on-chain in full.

## Architecture

- **Contract**: single GenLayer Intelligent Contract (`contracts/cassandra.py`), no factory/pool split
- **Frontend**: Vite + React + TypeScript + react-router-dom, deployed on Vercel
- **No backend, no database, no indexer** - everything reads directly from the contract RPC
- **Wallet**: standard injected EIP-1193 provider (Rabby, MetaMask), no MetaMask Snaps

## Contract lifecycle

```
DRAFTING -> RATIFIED -> UNDERWRITING -> ACTIVE -> RESOLVING -> SETTLED
                                                             -> DISPUTED -> SETTLED (via appeal)
```

| Status | Description |
|---|---|
| DRAFTING | Warning submitted; source verified and claim drafted by validator consensus |
| RATIFIED | Claim drafted and ratified |
| UNDERWRITING | Liquidity provided, open for coverage purchases |
| ACTIVE | Coverage purchased, resolution can be triggered once the resolution window opens |
| RESOLVING | Evidence submitted, validators judging occurrence + linkage |
| SETTLED | Resolution finalized, payouts distributed |
| DISPUTED | Settlement appealed by a stakeholder (submitter/coverage holder/LP), pre-transfer only |

## Five categories

| Category | Evidentiary standard |
|---|---|
| security | On-chain tx hashes, named security firm report |
| depeg | 24hr oracle deviation data showing peg breach |
| regulatory | Official government, court, or regulator publication |
| climate | Verified meteorological data from a recognized agency |
| systemic | Correlated on-chain or market data across the warned dependency chain |

## Security review fixes (2026-08-03)

Fixes applied in response to review from Pavel Kolosov:

- **Value conservation**: prophet's cut is deducted from the coverage pool rather than paid on top of a full payout - `prophet_share + sum(holder payouts) == total_coverage` exactly, in both outcomes. All positions zeroed post-settlement so no stale/double-claimable balances remain.
- **Resolution window enforcement**: resolution cannot be triggered before the window opens; window bounds are passed to validators so evidence outside the warned window is rejected.
- **Appeals**: only accepted pre-settlement (RESOLVING, never SETTLED - transfers can't be clawed back), require standing (submitter/coverage holder/LP), and `finalize_appeal` re-adjudicates via a fresh validator judgment rather than accepting a caller-supplied verdict.
- **Source verification**: `draft_prophecy` fetches `source_url` and requires the model to confirm it genuinely supports the warning before drafting.
- **Strict boolean parsing**: validator true/false judgments are now type-checked, rejecting stringly-typed booleans that Python's `bool()` would silently coerce.

See `tests/test_review_fixes.py` for the regression suite covering balances, timing, malicious evidence, authorization, replay, and appeal reversal.

## Local development

```bash
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.local.example` to `frontend/.env.local`.

## Running tests

```bash
pytest tests/test_cassandra.py -v
pytest tests/test_review_fixes.py -v
```

StudioNet enforces rate limits (30 req/min, 500 req/hour, 5000 req/day) - tests use module-scoped fixtures and sleeps between scenarios to stay under the ceiling.
