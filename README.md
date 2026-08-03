# CASSANDRA

Parametric insurance that pays out when documented public warnings come true, adjudicated by GenLayer's AI-validator consensus rather than a single arbiter or price feed.

Live: [the-cassandra.vercel.app](https://the-cassandra.vercel.app)

## What it does

A prophet submits a public warning with a source URL and verbatim quote. GenLayer's validator network drafts it into a falsifiable claim with an evidentiary standard and resolution window. Liquidity providers underwrite the pool; buyers pay a premium for coverage. When evidence is submitted, validators independently fetch and read it, then judge two questions: did the event occur, and is it causally linked to the original warning? If they reach consensus that it was vindicated, coverage holders are paid out. If not, premiums are retained by liquidity providers as yield.

Every resolution rationale is stored on-chain in full.

## Architecture

- **Contract**: single GenLayer Intelligent Contract (`contracts/cassandra.py`) deployed on StudioNet at `0x128A3ce1dfa92D15392E292Cd661B5680F08F31A`
- **Frontend**: Vite + React + TypeScript + react-router-dom, deployed on Vercel
- **No backend, no database, no indexer** - everything reads directly from the contract RPC

## Contract lifecycle

```
DRAFTING -> RATIFIED -> UNDERWRITING -> ACTIVE -> RESOLVING -> SETTLED
                                                             -> DISPUTED -> FINAL
```

| Status | Description |
|---|---|
| DRAFTING | Warning submitted, awaiting validator draft |
| RATIFIED | Claim drafted and ratified by validator consensus |
| UNDERWRITING | Liquidity provided, open for coverage purchases |
| ACTIVE | Coverage purchased, resolution can be triggered |
| RESOLVING | Evidence submitted, validators judging |
| SETTLED | Resolution finalized, payouts distributed |
| DISPUTED | Settlement appealed |
| FINAL | Appeal resolved |

## Five categories

| Category | Evidentiary standard |
|---|---|
| security | On-chain tx hashes, named security firm report |
| depeg | 24hr oracle deviation data showing peg breach |
| regulatory | Official government, court, or regulator publication |
| climate | Verified meteorological data from a recognized agency |
| systemic | Correlated on-chain or market data across the warned dependency chain |

## Local development

```bash
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.local.example` to `frontend/.env.local` and set:

```
VITE_CASSANDRA_ADDRESS=0x128A3ce1dfa92D15392E292Cd661B5680F08F31A
VITE_GENLAYER_RPC=https://studio.genlayer.com/api
VITE_GENLAYER_CHAIN_ID=61999
```

## Running tests

Tests require Python with `gltest` and the GenLayer SDK installed.

```bash
# Full regression suite
pytest tests/test_cassandra.py -v

# Five verdict E2E tests (deploys a fresh contract, takes ~10 min)
pytest tests/test_five_verdicts.py -v

# Canonical contract lifecycle (runs against the deployed address)
pytest tests/test_canonical_lifecycle.py -v
```

StudioNet enforces a 30 req/min and 500 req/hr rate limit. The test suite uses module-scoped fixtures and sleeps between scenarios to stay under the ceiling.

## Wallet

Connect Rabby or MetaMask. The app uses standard EIP-1193/EIP-3326/EIP-3085 - no MetaMask Snaps. Chain switching to StudioNet (chain ID 61999) is handled automatically on connect.

## Vercel deployment

Set these environment variables in the Vercel project settings:

| Key | Value |
|---|---|
| `VITE_CASSANDRA_ADDRESS` | `0x128A3ce1dfa92D15392E292Cd661B5680F08F31A` |
| `VITE_GENLAYER_RPC` | `https://studio.genlayer.com/api` |
| `VITE_GENLAYER_CHAIN_ID` | `61999` |
