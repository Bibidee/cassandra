# CASSANDRA
### *The protocol that believed the warnings*
**Product, Protocol & Design Specification — v0.1**

---

## 0. The Myth (Why This Name)

In Greek myth, Cassandra was given the gift of true prophecy — and the curse that no one would ever believe her. She warned Troy about the horse. She was right. Nobody listened. The city burned anyway.

Every crypto cycle has its Cassandras. The audit that flagged the reentrancy bug six months before the exploit. The risk report that called the depeg. The analyst thread that said "this bridge is one multisig away from disaster" — three weeks before it was.

**Nobody pays the people who were right. Nobody insures against the world's refusal to listen.**

CASSANDRA does. It is a parametric insurance protocol that pays out when a **documented, public warning** turns out to have been correct — validated not by a single arbiter, but by GenLayer's AI-validator consensus reading both the original warning and the real-world outcome, and judging whether the two are causally and substantively linked.

This is not "if X happens, pay out." Every existing parametric product does that with a price feed. CASSANDRA is "if someone said X would happen, for identifiable reasons, and X happened for those reasons — pay out." That sentence cannot be executed by a deterministic oracle. It requires reading comprehension, causal reasoning, and judgment under ambiguity. It requires GenLayer.

---

## 1. Product Overview

### 1.1 What it is

CASSANDRA lets anyone create a **Prophecy Pool**: a bounded insurance market tied to one specific, evidenced warning. Buyers purchase coverage against the event the warning describes. If the AI-validator consensus determines, at resolution time, that (a) the warning was substantively about the class of event that occurred, and (b) the event did in fact occur, and (c) a reasonable causal or thematic link exists between them — the pool pays out. If the warning didn't come true, premiums are retained by liquidity providers as yield.

### 1.2 Who it's for

- **DeFi protocols & DAOs** — insure treasury/TVL against warned-about exploits, depegs, oracle failures.
- **LPs & risk-seeking capital** — underwrite prophecy pools for premium yield, effectively betting "the warning was wrong" or "nothing happens."
- **Researchers, auditors, analysts** — anyone whose public warning becomes a pool gains reputation and can optionally receive a **prophet's cut** of payouts triggered by their own calls.
- **GenLayer ecosystem builders** — the flagship demonstration that Intelligent Contracts can adjudicate meaning, not just numbers.

### 1.3 Core loop

```
1. SEED     — Someone submits a Warning (source URL, quote, timestamp, category)
2. FORGE    — CASSANDRA's leader validator drafts a Prophecy: a structured,
              falsifiable claim extracted from the warning + a resolution window
2b. RATIFY  — Validator quorum confirms the Prophecy fairly represents the warning
3. UNDERWRITE — LPs stake into the pool; buyers pay premium for coverage
4. WATCH    — Oracle/web-access monitors relevant sources through the window
5. RESOLVE  — At window close (or on trigger claim), AI validators independently
              assess: did it happen, and does it match the prophecy? Consensus
              required across independent validators (Optimistic Democracy)
6. SETTLE   — Payout to coverage holders + prophet's cut, or premium to LPs
7. APPEAL   — Disputed resolutions escalate to a larger validator set
```

---

## 2. The Adjudication Problem (Why GenLayer, Specifically)

Three genuinely non-deterministic judgment calls sit at the core of every Prophecy, and CASSANDRA is explicit that none of them are solvable by a price feed:

1. **Extraction** — turning a messy human warning ("I think this bridge multisig setup is asking for trouble") into a falsifiable, resolvable claim with a defined event class, evidentiary bar, and time window. This is an LLM drafting task with adversarial incentive to game it — so it goes through leader-propose + validator-ratify, not a single call.

2. **Occurrence** — did the event class actually happen? For code exploits this can lean toward stronger evidence (on-chain data, post-mortems). For narrative/regulatory/climate prophecies it requires reading live web sources and forming a judgment about ambiguous, evolving situations.

3. **Linkage** — is the thing that happened actually *the thing that was warned about*, or a coincidence being opportunistically claimed? This is the hardest and most novel judgment: causal/thematic matching between two pieces of natural language separated by time. This is the part no other protocol on any chain can currently do trustlessly.

Every one of these is an equivalence-principle decision, not a business-logic decision, and each is documented per-Prophecy in the contract's `resolution_rationale` field so it is auditable after the fact — this is a transparency commitment, not just an implementation detail.

---

## 3. Prophecy Taxonomy (Launch Categories)

| Category | Example Warning | Example Payout Trigger |
|---|---|---|
| **Security** | Audit/thread flags a specific vulnerability class in a live contract | Exploit occurs matching the flagged vector within window |
| **Depeg / Stability** | Analyst warns a stablecoin's backing is impaired | Peg breaks past threshold, causally linked to the warned mechanism |
| **Regulatory** | Legal analysis warns a jurisdiction is preparing hostile action | Action is taken matching the warned scope, within window |
| **Climate / Parametric-classic** | Climate model/report warns of drought/flood risk in a region | Verified weather data confirms the event, in the warned region/window |
| **Systemic / Macro** | Risk report warns of a correlated cascade (e.g., "X depeg will cascade to Y, Z") | Cascade occurs matching the warned dependency chain |

Security and climate are the two flagship launch verticals: security proves CASSANDRA works where evidence is crisp (on-chain), climate proves it works in classic parametric territory with real-world data feeds — a direct upgrade path from the original brief.

---

## 4. Visual & Brand Identity

### 4.1 Design thesis

Every parametric insurance site in this space looks the same: blue/teal fintech gradients, clean sans-serif, trust-through-blandness. CASSANDRA rejects that entirely. The visual language is **scorched manuscript meets ancient warning meets modern terminal** — the aesthetic of a prophecy that was written down, ignored, and burned along with the city, now excavated and running on-chain.

This is deliberately *uncomfortable* in a category that usually plays it safe. That discomfort is the point — it signals "we are not another insurance dashboard."

### 4.2 Color System — "Ember & Ash"

No blues. No teals. No SaaS-purple. This palette does not exist elsewhere in the GenLayer ecosystem or in parametric insurance generally.

| Token | Hex | Role |
|---|---|---|
| `--ash-void` | `#0E0A03` | Primary background — near-black warm charcoal, like burnt paper |
| `--ash-surface` | `#1A140A` | Card/panel background |
| `--ash-surface-raised` | `#241C0F` | Elevated surfaces, modals |
| `--ember-primary` | `#E84D0E` | Primary action color — burnt orange-red, "the fire" |
| `--ember-hot` | `#FF6B1A` | Hover/active states, urgency |
| `--gold-prophecy` | `#F5C842` | Accent — "the truth revealed," used for validated/resolved states, key numbers |
| `--blood-warning` | `#6B0F1A` | Danger, unresolved risk, active claim states |
| `--rust-clay` | `#C4602A` | Secondary accent, borders, dividers |
| `--sage-vindicated` | `#4A8C7E` | The ONE cool color in the palette — reserved exclusively for "prophecy fulfilled / payout settled" states. Its rarity is the point: green in this system doesn't mean "go," it means "the warning was right." |
| `--parchment` | `#EDE5D0` | Primary text on dark |
| `--parchment-dim` | `#8A7A60` | Secondary text, captions |
| `--ink-faint` | `#5A4A30` | Tertiary text, disabled |

Gradient usage is restricted to exactly one signature gradient, used sparingly (hero text, key CTAs only): `linear-gradient(135deg, #E84D0E 0%, #F5C842 50%, #C4602A 100%)` — "the ember gradient."

### 4.3 Typography

- **Display / headings:** A high-contrast serif with historical weight — `Fraunces`, `Newsreader`, or `Georgia` fallback. Prophecies are *written*, not designed; headlines should feel carved, not typeset.
- **Body:** `Space Grotesk` or `Inter` — clean, contemporary, so the interface itself doesn't tip into costume/theme-park territory. The ancient/modern contrast is the whole trick: mythic content, contemporary chrome.
- **Data / monospace:** `Space Mono` or `JetBrains Mono` for addresses, hashes, timestamps, validator IDs, countdown timers — anything that needs to read as *system output*, distinct from the "prophecy text" which reads as *human testimony*.

### 4.4 Motif system

- **The Seal** — every Prophecy gets a circular wax-seal-style glyph generated deterministically from its content hash (simple SVG, procedural, not an NFT-art-generator dependency). Unresolved = ash-grey seal, cracked. Vindicated = gold seal, whole. Falsified = seal shown broken/scattered.
- **The Flame line** — a thin animated ember-orange line that "burns" across progress bars, countdown timers, and resolution progress — rendered as a gradient sweep, not a literal flame icon. No flat blue progress bars anywhere in this product.
- **Scorch texture** — subtle, extremely low-opacity (3-6%) noise/burn-edge textures at panel corners only. Never full-bleed, never distracting, never used as a background gradient mesh (flat design elsewhere).
- **NO generic insurance iconography** — no umbrellas, no shields, no checkmarks-in-circles. Iconography vocabulary instead: eye (foresight), flame (the warning made real), scroll/tablet (the recorded warning), broken/whole seal (outcome).

### 4.5 UI Principles

- **Flat, no drop shadows, no glassmorphism.** Depth communicated via subtle border color shifts and the surface token ladder (`void` → `surface` → `surface-raised`), not blur or shadow.
- **The Prophecy Card is the atomic unit** of the entire UI — every pool, every claim, every resolution renders through this one component: seal glyph, original warning quote (in serif, styled as an inset quotation), structured claim (in mono, styled as system-parsed data), status, pool size, resolution window countdown.
- **Validator reasoning is always visible**, never hidden behind a tooltip. A collapsible "Why did this resolve this way?" panel shows the actual resolution rationale text from the contract — this is the trust mechanism, and hiding it would undercut the entire premise of the product.
- **Dark mode only at launch.** This palette does not have a coherent light-mode inverse and forcing one would dilute the identity; revisit post-launch if requested.

---

## 5. Information Architecture (Frontend)

```
/                     Landing — myth framing, live prophecy ticker, "how it works"
/prophecies           Browse all pools — filter by category, status, resolution window
/prophecies/:id       Prophecy Card detail — warning, claim, pool stats, buy coverage,
                       provide liquidity, resolution rationale (once resolved)
/submit               Seed a new Warning → guided flow to Prophecy drafting
/portfolio            User's coverage positions, LP positions, prophet's-cut claims
/prophet/:address     Public track record of a warning source — win rate, categories
/how-it-works         Deep explainer: Optimistic Democracy, appeal flow, equivalence
                       principle explained in plain language
```

### 5.1 Landing page narrative arc

1. **Hero** — the myth in one line, ember gradient headline: *"Every warning that came true, and nobody paid for it. Until now."*
2. **Live ticker** — real prophecy pools scrolling, seal glyphs, mono countdown timers
3. **How it resolves** — 3-step visual: Warning → AI Validator Consensus → Settlement, explicitly naming Optimistic Democracy without jargon-dumping
4. **Categories** — the 5 launch verticals as cards
5. **Trust panel** — link to a resolved prophecy with full rationale visible, proving the system isn't a black box
6. **CTA split** — "Insure against a warning" vs. "Underwrite a pool" (buyer vs. LP funnels, always kept visually distinct — different primary color weight)

---

## 6. Protocol Mechanics (Summary — see Build Brief for contract-level detail)

- **Prophecy Pool** = an Intelligent Contract instance holding staked liquidity, sold coverage, a structured claim, a resolution window, and a resolution state machine.
- **Roles:** Warning Submitter (optional prophet's cut), LPs (premium yield, capital at risk), Coverage Buyers (premium paid, payout on validated resolution), Validators (GenLayer network — consensus on Extraction, Occurrence, Linkage).
- **Resolution states:** `Drafting → Ratified → Underwriting → Active → Resolving → Settled` (+ `Disputed → Appealed → Final` branch).
- **Payout curve:** binary at launch (full payout or none) — tiered/partial payout (e.g., "70% confidence match → 70% payout") is a v2 consideration flagged for design but not required at launch, to keep the resolution logic auditable and simple.
- **Anti-gaming:** a warning must have a public, timestamped, immutable-enough source (URL + archive snapshot recommended) predating the Prophecy's creation, so post-hoc "warnings" can't be submitted after an event is already known.
- **Real value movement (v0.1.1):** `provide_liquidity` and `buy_coverage` are `@gl.public.write.payable` and read the actual GEN sent (`gl.message.value`), not a caller-supplied integer. `settle()` moves real GEN via a `gl.evm.contract_interface`-wrapped `_Recipient(...).emit_transfer(value=...)` proxy — the standard GenVM pattern for native-currency payouts to a plain address. Vindicated: prophet gets their cut, each coverage holder is paid their full coverage amount. Not vindicated: each LP is repaid their principal plus a pro-rata share of the collected premiums as yield. Verified live on StudioNet with exact-wei accounting.

---

## 7. Tone of Voice

Mythic but not cosplay. Confident but not hyped. CASSANDRA speaks like it already knows how this ends — a little weary, a little vindicated. Copy examples:

- Empty state: *"No prophecies yet. The silence before the warning."*
- Resolved-true state: *"It happened. Exactly as warned."*
- Resolved-false state: *"This one didn't come true. The city stands."*
- Error/failure state: *"The oracle is unclear. Try again."*

Avoid: exclamation points, "🚀", "revolutionary," any language indistinguishable from a generic DeFi launch tweet.

---

## 8. Open Design Questions — Resolved (v0.1 → v0.1.1)

1. **Prophet's cut: opt-in per submitter**, not a protocol-wide constant. Implemented as `prophet_cut_bps` on `submit_warning`, capped at 2000 bps (20%). Each submitter sets their own cut at seed time.
2. **Binary payout confirmed for v1.** No tiered/partial-payout logic implemented. Revisit before mainnet if warranted, but out of scope for this build.
3. **The LLM's draft is not shown to the submitter for feedback before Ratification.** Reaching validator consensus on the leader's draft *is* the ratification step (`draft_prophecy`) — there is no intermediate submitter review loop, since that would be a direct manipulation vector (a submitter could pressure or iterate the wording to make resolution easier to win before validators lock it in).
4. **Category-specific evidentiary guidance implemented.** `CATEGORY_EVIDENTIARY_GUIDANCE` in `contracts/cassandra.py` gives the drafting LLM a fixed per-category standard (on-chain evidence for security/depeg, official publications for regulatory, recognized meteorological agencies for climate, correlated on-chain/market data for systemic), injected into every `draft_prophecy` prompt so the evidentiary bar stays consistent across every Prophecy in the same category rather than being invented ad hoc. Verified live on StudioNet: a climate-category warning correctly produced an evidentiary standard citing "national weather service, NOAA, or validated remote-sensing datasets."

---

*End of Product, Protocol & Design Specification v0.1. See companion document: `CASSANDRA_Coding_Agent_Build_Brief.md` for implementation instructions.*
