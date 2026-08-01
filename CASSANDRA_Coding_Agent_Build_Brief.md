# CASSANDRA — Coding Agent Build Brief
**For: an autonomous coding agent (Claude Code + GenLayer skills) implementing this project**
**Companion doc:** `CASSANDRA_Product_Design_Spec.md` (read that first for product/narrative/design context — this doc is execution-only)

---

## 0. Scope Lock

- **Frontend + Intelligent Contracts only.** No backend service, no Fly.io, no Supabase, no custom server of any kind. All state lives on-chain in GenVM contracts; the frontend talks to GenLayer directly via `genlayer-js`.
- **Target network for build/dev: StudioNet** (chain id `61999`, RPC `https://studio.genlayer.com/api`). Gasless — 0 GEN balance is expected and correct.
- **Wallet:** injected wallet via `genlayer-js` (no custom auth, no email/password anywhere).
- **`genlayer-js` version pinned:** `1.1.8`.
- Do not invent SDK method names. Verify every `genlayer-js` / `genlayer-py` call against the docs MCP or SDK reference before writing it.

---

## 1. Pre-flight (run once, in order)

```bash
npm install -g genlayer
pip install genvm-linter
pip install genlayer-test
```

```
/plugin marketplace add genlayerlabs/skills
/plugin install genlayer-dev@genlayerlabs
```

```
claude mcp add genlayer-docs --transport sse https://docs-mcp.genlayer.com/sse
claude mcp add genlayer npx -- -y genlayer-mcp
```

Confirm network target:
```bash
genlayer network set studionet
```
(If StudioNet is not an available preset name, use `genlayer network list` to find the exact name/id before proceeding — do not hand-roll RPC config.)

If any install step fails (npm registry auth, pip permissions, plugin marketplace unreachable), **stop and report exactly what failed and the next manual command** — do not silently skip to hand-written alternatives.

---

## 2. Project Structure

```
cassandra/
├── contracts/
│   ├── prophecy_pool.py          # core Intelligent Contract — one instance per prophecy
│   ├── prophecy_factory.py       # deploys new prophecy_pool instances, tracks registry
│   └── lib/
│       ├── equivalence.py        # shared leader/validator comparison functions
│       └── schemas.py            # dataclasses for Warning, Prophecy, ResolutionResult
├── tests/
│   ├── direct/
│   │   ├── test_prophecy_lifecycle.py
│   │   ├── test_extraction.py
│   │   ├── test_resolution_linkage.py
│   │   └── test_access_control.py
│   └── integration/
│       ├── test_full_resolution_flow.py
│       └── test_appeal_flow.py
├── frontend/
│   ├── src/
│   │   ├── lib/genlayer-client.ts   # createClient, chain config, typed contract schema
│   │   ├── config/contracts.ts      # deployed addresses + ABI/schema per environment
│   │   ├── components/
│   │   │   ├── ProphecyCard.tsx
│   │   │   ├── SealGlyph.tsx        # procedural SVG seal, deterministic from content hash
│   │   │   ├── FlameProgress.tsx    # ember gradient progress/countdown
│   │   │   └── ResolutionRationale.tsx
│   │   ├── pages/                   # per IA in design spec section 5
│   │   └── styles/tokens.css        # design tokens from spec section 4.2 as CSS custom props
│   └── package.json
└── README.md
```

---

## 3. Contract Design

### 3.1 `prophecy_pool.py` — state (storage types only, never raw dict/list)

Use GenLayer storage primitives exclusively:

- `TreeMap[Address, u256]` for coverage positions (buyer → amount insured)
- `TreeMap[Address, u256]` for LP stakes
- `dataclass` (with `allow_storage`) for `Warning` (source_url, quote_text, submitted_at, submitter_address, category)
- `dataclass` (with `allow_storage`) for `Prophecy` (structured_claim, resolution_window_start, resolution_window_end, evidentiary_standard)
- `dataclass` for `ResolutionResult` (occurred: bool, linkage_confidence: enum/int, rationale: str, resolved_at)
- Sized integers for all money fields — never plain Python `int` assumed unbounded; use the GenVM-provided sized types per the write-contract skill guidance.
- Status as an enum: `DRAFTING | RATIFIED | UNDERWRITING | ACTIVE | RESOLVING | SETTLED | DISPUTED | APPEALED | FINAL`

### 3.2 Core methods (public contract interface — verify exact decorator/signature patterns via `write-contract` skill before implementing)

| Method | Type | Purpose |
|---|---|---|
| `submit_warning(source_url, quote_text, category)` | write | Seed step — stores raw Warning, triggers drafting |
| `draft_prophecy()` | write, **non-deterministic (LLM)** | Leader extracts structured, falsifiable claim from Warning via LLM call |
| `ratify_prophecy()` | write, **non-deterministic (consensus)** | Validator quorum confirms draft fairly represents the warning — custom validator function, NOT strict_eq |
| `provide_liquidity(amount)` | write | LP stakes into pool |
| `buy_coverage(amount)` | write | Buyer pays premium, gets coverage position |
| `trigger_resolution()` | write, **non-deterministic (LLM + web)** | Callable after window opens; leader assesses Occurrence + Linkage using live web access |
| `settle()` | write | Executes payout or premium-retention based on ResolutionResult |
| `appeal()` | write | Escalates a Disputed resolution to larger validator set |
| `get_prophecy_state()` | read | Full state for frontend rendering |
| `get_resolution_rationale()` | read | Returns the stored rationale text — **must always be populated on any resolved state**, this is the trust mechanism from the design spec, non-negotiable |

### 3.3 Equivalence Principle strategy (per method — decide BEFORE writing logic)

This is the most important section in this brief. Get this wrong and the whole product is either ungameable-but-useless or flexible-but-exploitable.

- **`draft_prophecy` (Extraction):** custom leader + validator functions. Leader LLM proposes structured claim JSON; validators independently re-derive from the same source Warning and compare for *substantive* equivalence (same event class, same evidentiary bar, same rough timeframe) — NOT exact string match. `strict_eq` is wrong here; the prose will never be byte-identical.
- **`ratify_prophecy`:** validator quorum vote on whether the drafted claim fairly represents the original warning (yes/no + reasoning), aggregated by majority per Optimistic Democracy norms.
- **`trigger_resolution` (Occurrence + Linkage):** the hardest non-determinism in the whole contract. Leader fetches current web/news evidence (fetch via GenVM web access per `write-contract` skill guidance), forms a judgment on Occurrence and Linkage separately, and returns a structured result including confidence and rationale text. Validators independently repeat the same fetch-and-judge process against the same claim, and consensus equivalence is on the *conclusion* (did it happen / is it linked), with rationale texts stored individually per validator for auditability — not required to match verbatim.
- **`settle`:** deterministic — once ResolutionResult is finalized by consensus, payout math is pure arithmetic (`strict_eq`-safe), no further judgment involved.
- For every non-deterministic method: define and document the exact leader/validator function pair explicitly in code comments referencing this brief section, since a future maintainer must be able to see the reasoning, not just the code.

### 3.4 LLM output defense (mandatory per method touching an LLM)

- Always request strict JSON output with an explicit schema in the prompt.
- Validate types on every field after parse; handle common key aliasing (e.g. `"occurred"` vs `"did_occur"`) defensively.
- Sanitize/repair malformed JSON before failing outright (strip markdown fences, trailing commas) — but if unrecoverable, fail with a deterministic classified error, never a silent default.
- Error prefixes: `EXPECTED_` (e.g. insufficient evidence to resolve yet), `EXTERNAL_` (source fetch failed), `TRANSIENT_` (retry-safe), `LLM_ERROR_` (malformed/unusable model output).

### 3.5 `prophecy_factory.py`

- Minimal registry contract: `deploy_prophecy(warning_params) -> address`, plus `TreeMap[u256, Address]` index and category filters for the frontend's `/prophecies` browse view. Keep this contract intentionally thin — all real logic lives in `prophecy_pool.py` instances.

---

## 4. Quality Gates — run in this exact order, every contract change

```bash
genvm-lint check contracts/prophecy_pool.py --json
genvm-lint check contracts/prophecy_factory.py --json
```
Fix all errors before proceeding — do not move to tests with lint errors outstanding.

```bash
pytest tests/direct/ -v
```
Direct tests must cover, at minimum: full lifecycle happy path, access control (non-owner can't ratify/settle), extraction edge cases (malformed source, missing quote), and linkage rejection (event occurred but doesn't match claim → no payout). Mock all web/LLM calls here.

```bash
gltest tests/integration/ -v -s
```
Run once direct tests are green and whenever consensus/web/LLM behavior actually matters — e.g. verifying the leader/validator equivalence functions behave sanely against StudioNet, not just mocks.

Deploy/debug loop:
```bash
genlayer deploy
genlayer schema <address>
genlayer call <address> get_prophecy_state
genlayer write <address> submit_warning ...
genlayer receipt <txHash> --stdout --stderr
```
If a transaction fails, always debug in this order: `receipt --stdout --stderr` → `schema <address>` → `code <address>` → re-read contract logic. Do not guess-edit the contract before reading the receipt.

---

## 5. Frontend Integration

### 5.1 Client setup (`lib/genlayer-client.ts`)

- Use `genlayer-js@1.1.8`'s `createClient` against the StudioNet chain config — verify exact chain object shape/import path against SDK reference before writing, do not assume from memory.
- Connect via injected wallet (browser extension) — no custom auth flow, no stored credentials, no password fields anywhere in this app (hard constraint from the operating rules this agent runs under).
- Generate/pull the deployed contract schema (`genlayer schema <address>`) and keep a typed representation of it in `config/contracts.ts` — do not hand-write a duplicate ABI that can drift from the deployed contract.

### 5.2 Read vs. write UX (mandatory)

Every contract interaction in the UI must visibly distinguish:
- **Read/view calls** (e.g. `get_prophecy_state`) — no wallet prompt, no status stepper.
- **Write/transaction calls** (e.g. `submit_warning`, `buy_coverage`) — must show explicit **submitted → pending → finalized → failed** states, using the FlameProgress component (ember gradient sweep) from the design spec, never a generic spinner.

### 5.3 Component build order (build in this sequence, test each in isolation before composing)

1. `styles/tokens.css` — all colors/fonts from design spec §4.2–4.3 as CSS custom properties, both light... **no, dark-mode-only per spec §4.5** — do not build a light theme.
2. `SealGlyph.tsx` — pure deterministic SVG generator from a content hash string, three visual states (unresolved/cracked, vindicated/gold-whole, falsified/broken). No external image assets.
3. `FlameProgress.tsx` — reusable progress/countdown bar, ember gradient sweep animation.
4. `ProphecyCard.tsx` — composes the above; this is the atomic UI unit per design spec §4.5, get it right before building any page.
5. `ResolutionRationale.tsx` — collapsible panel rendering `get_resolution_rationale()` output verbatim; must never truncate or summarize the on-chain rationale text.
6. Pages per IA in design spec §5, in order: `/prophecies` (list) → `/prophecies/:id` (detail, wires in write calls) → `/submit` → `/portfolio` → `/prophet/:address` → `/` (landing, build last since it's marketing composition of already-built pieces) → `/how-it-works`.

### 5.4 Explicit non-goals (do not build these even if convenient)

- No backend API layer of any kind.
- No database — all reads come from contract state via `genlayer-js`.
- No custom indexer service; if historical/aggregate views (e.g. prophet win-rate) need more than direct contract reads can efficiently provide, surface that limitation rather than standing up infrastructure to solve it, and flag it back to the user as an open question.
- No light theme.
- No generic insurance iconography (umbrellas/shields/checkmarks) — see design spec §4.4.

---

## 6. Definition of Done (v1 / demo-ready)

- [ ] `prophecy_pool.py` and `prophecy_factory.py` pass `genvm-lint` clean
- [ ] All direct tests green, including the linkage-rejection edge case
- [ ] At least one full integration test run on StudioNet: submit → draft → ratify → underwrite → buy coverage → resolve → settle
- [ ] Frontend deployed locally, wallet connects via injected provider, all 7 IA pages render against a real deployed instance (not mocked data)
- [ ] `ResolutionRationale` panel visibly shows real validator reasoning text pulled from chain for at least one resolved demo prophecy
- [ ] Design tokens applied consistently — no default browser blue, no leftover Tailwind default palette colors anywhere in the shipped UI
- [ ] README documents: how to redeploy, how to point frontend at a new contract address, and the exact StudioNet network config used

---

## 7. If Something Is Blocked

State exactly what's blocked and the next concrete command/step. Known likely blockers and their owners:
- **Faucet/testnet GEN** — browser-based claim, cannot be automated; ask the user to claim manually if moving past StudioNet.
- **`genlayer-js` API surface uncertainty** — stop and verify via docs MCP or SDK reference (`https://sdk.genlayer.com/main/_static/ai/api.txt`) rather than guessing a method name.
- **Web-access non-determinism in `trigger_resolution`** — if live web fetch during integration tests is flaky, that's expected; the equivalence function should be judged on *conclusion* stability across validator runs, not byte-identical fetch results. Do not "fix" this by weakening it to `strict_eq`.

---

*This brief assumes the reader has already read `CASSANDRA_Product_Design_Spec.md`. Do not re-derive product rationale from this document — it is execution-only.*
