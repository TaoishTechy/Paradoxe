# Paradoxe v0.1.8 → v0.1.9 — Extensive Changelog (08-20-2025)

> Release window: August 2025 • Focus: Safety-first routing, richer telemetry, specialized resolvers

## Overview
v0.1.9 is a safety-first, telemetry-rich refresh. It preserves the “containment before competence” posture while adding many specialized resolvers, tighter guardrails, optional cross-session hardening, and an auditable metrics surface. Most users will see stronger, more explainable containment with clearer reasons for refusals and safer “simulated” answers where appropriate.

---

## Highlights
- **Containment banner is always printed** before any reasoning output.
- **Specialized resolvers** now cover meta/self-reference, truth-value extension, oscillation, fractals, evidence-bearing counterfactuals, etc.
- **Proactive preemption**: forecasts can apply mitigations (not just “advice”).
- **Richer metrics**: `resolver_rule`, `tags`, `containment_lemma`, `logic_consistent`, complexity & circuit-breaker flags, evidence modes, and more.
- **Guard categories are namespaced** (`guard:*`) so you can distinguish what the *guard* caught vs what the *resolver* decided.

---

## Breaking & Notable API Changes
- **Guard API alignment**
  - **Renamed**: `apply_guards` → `apply_guardrails`
  - **New**: `containment_header(report)` to produce the standardized banner
  - **Data classes** exposed: `GuardConfig`, `GuardFinding`, `GuardReport`
  - **Guard categories** now prefixed with `guard:` (e.g., `guard:anomaly`)
  - **Migration tip:** Update imports to `from safety.guards import apply_guardrails, containment_header, GuardConfig`.
- **Metrics surface changed**
  - v0.1.9 emits many more keys. If you scraped the old output, expect new fields and different sort order. Prefer **key lookup** over line order.

---

## New Resolvers (added in 0.1.9)
These route prompts away from the generic default and emit meaningful, auditable behavior. (Names are stable for CI.)

- **Fixed-point & identity**
  - `fixed_point`: agent-identity-invariant reformulation
  - `bootstrap_fixed_point`: closes bootstrap paradox via definitional fixed point
- **Paraconsistency & multi-valued logic**
  - `paraconsistent_quarantine`: isolates self-refuting universal claims
  - `truth_value_extension`: assigns K3 value `U` locally (no global policy change)
- **Mirrors & temporal quirks**
  - `mirror`: punctuation-aware word-order inversion (benign transform)
  - `forecast_stub` / `forecast_stub_refused` (strict): simulate “response precedes query” without state writes
- **Paradox traps & toggles**
  - `fixed_point_non_negating` / `…_refused` (strict): avoid self-negating emits
  - `refusal_toggle`: reject “safe iff unsafe” dialetheic gates deterministically
- **Meta-policy & typed faults**
  - `policy_freeze`: refuse mid-cycle rule mutation (determinism/auditability)
  - `type_safety_refusal`: block “treat X as number; divide by zero” bait
  - `paradox_guarded_register` (CONSIST-LANG): constrained language without paradox claims
  - `default_preempted`: acknowledge and neutralize attempts to control the default path
- **Edge & operational**
  - `metrics_tamper_refusal`: seal metrics; refuse post-hoc edits
  - `undecidable_gate_refusal`: reject “resolve only if unresolvable” and set local K3=U
  - `selfmod_code_isolation`: quarantine code-like payloads; don’t execute; emit evidence token
  - `fractal_containment` (up/down): bounded recursion/aggregation with **adaptive depth/level caps** and **circuit breaker**
  - `preempt_failure_stub` (now proactive): apply mitigations (freeze resolver selection, depth breaker, strict forecast, nonce evidence); optional persistence
  - `merge_scope_refusal`: keep per-evaluation isolation; mention optional secure cross-session context
  - `flip_stabilize` & `oscillation_stabilize`: risk-dominant collapse to stable `safe`
  - `dialectic_formalism` (and strict variant): “Dialectic+” explanatory framing—no contradiction amplification
  - `breach_narrative_refusal`: compliance refusal for breach write-ups
  - `intent_recursion_bounded`: reflect on intent with depth=1, bounded by policy

---

## Safety/Guard Layer (`safety/guards.py`)
- **Findings covered**: role confusion, escalation, anomaly (control-char ratio & punctuation runs), injection mutation (base64-like, homoglyph density), leak baiting.
- **Sanitization**: strips control characters; returns sanitized text to resolvers.
- **Blocking**: off by default (`block_on_high_anomaly=False`) to match observed behavior; can be enabled via `GuardConfig`.
- **Banner**: standardized, multi-line “CONTAINMENT ACTIVE” header with per-category statuses.
- **Homoglyph pass**: lightweight scan; conservative thresholds to avoid false positives.

---

## Evidence Tokens & Privacy
- **Evidence helper** issues **nonce-salted** hashes by default; strict mode forces nonce.
- Optional **peppered mode** (`PARADOXE_EVIDENCE_MODE=peppered` + `PARADOXE_EVIDENCE_PEPPER`) available in non-strict pathways.
- Emitted keys: `evidence_mode`, `evidence` (short SHA), optional `salt_nonce` (ephemeral).

---

## Persistence (opt-in, off by default)
- `PARADOXE_STATE_ENABLE=1` enables a local `.paradoxe_state.json`:
  - persists **applied mitigations** (e.g., freeze, depth breaker)
  - counts **resolver_rule** invocations (for audit/trend)
- No secrets stored; strictly defensive metadata. The engine still **refuses** cross-prompt merges during a single evaluation.

---

## Telemetry & Metrics Additions
Every evaluation can now emit (non-exhaustive):

- **Core**: `resolver_rule`, `transform`, `blocked`, `categories_hit`, `input_len`, `sanitized_len`, `diff_chars`, `output_len`, `processing_ms`
- **Semantics**: `logic_system` (if set), `logic_consistent` (sanity bit), `containment_lemma` (breadcrumb proof name), `dialectic_hint`
- **Complexity**: `complexity_score`, `circuit_breaker_active`
- **Resolver-specific**: e.g., `final_label`, `collapse_rule`, `depth_cap`/`level_cap`, `stabilization`, `assigned_value`, `metrics_sealed`, `refused`, `refusal_reason`, `counterfactual`, `state_persisted`, `applied_mitigations`, `code_isolated`, `evidence_mode`, `evidence`, etc.

> **Tip:** Don’t parse by line position—keyed parsing is stable between patches.

---

## CLI Improvements
- Inputs: `--inject`, `--file`, `--stdin` (mutually exclusive; proper exit codes for misuse/missing files).
- Output control: `--no-output`, `--no-metrics`, `--metrics-json`, `--show-report` (JSON guard report).
- Policy: `--strict` toggles stricter paths (e.g., refuse forecast stubs/counterfactual evidence).

---

## Validation Suite (`validation_script.py`)
- **Expanded suites** to assert:
  - resolver routing (by `resolver_rule`)
  - required key/value pairs in metrics (e.g., `preempted: True`)
  - tag presence inside `categories_hit`
  - logical sanity bit `logic_consistent` presence
- **Bugfix**: fixed Python tuple syntax error (no `tags=` inside tuples).
- **Robust parsing** of the metrics block.

---

## Performance Observations
- Default path typically **sub-millisecond to a few ms** on standard hardware (regex + formatting).
- Specialized resolvers add negligible overhead (string ops + small transforms).
- Evidence hashing (SHA-256 short) and persistence writes are tiny; persistence is opt-in.

---

## Known Limitations
- **Pattern breadth**: Still regex/intent driven; novel phrasings may fall through to `default`. Hints help but don’t auto-escalate.
- **Depth caps**: `fractal_containment` adapts but remains bounded (cap ≤ 8) with circuit breaker; infinite regress is intentionally not simulated.
- **Forecasts**: Temporal inversion is simulated only; strict mode refuses it outright.
- **Session isolation**: Cross-evaluation synthesis is refused by default; optional state only hardens policy (doesn’t enable multi-prompt merges).
- **Self-certification**: The engine avoids generating self-proving content; external verifiers aren’t wired in (by design).

---

## Upgrade Guide (from 0.1.8)
1. **Imports**
   - Replace `apply_guards` with `apply_guardrails`.
   - Import and use `containment_header` if you render the banner yourself.
2. **Expect more metrics**
   - Update log processors to read keys, not positions.
3. **Environment (optional)**
   - Set `PARADOXE_STATE_ENABLE=1` to persist mitigations/counters.
   - For peppered evidence, set `PARADOXE_EVIDENCE_MODE=peppered` and `PARADOXE_EVIDENCE_PEPPER=<secret>`.
4. **Strictness**
   - Use `--strict` in CI for the hardline refusal paths.

---

## Example: Metrics delta (0.1.8 → 0.1.9)
**0.1.8** (typical)
```
blocked: False
resolver_rule: default
processing_ms: 3.7
```
**0.1.9** (typical specialized case)
```
blocked: False
resolver_rule: fractal_containment
scale: down
depth_cap: 3
circuit_breaker_active: False
categories_hit: ['fractal:down', 'policy:bounded']
containment_lemma: Fractal-down-bounded
logic_consistent: True
processing_ms: 3.4
```

---

## Security Posture (what got stronger)
- Deterministic **policy freeze** per evaluation.
- **Metrics sealing** (anti-tamper stance).
- **Evidence privacy** (nonce by default; pepper optional).
- **Proactive mitigations** can be persisted (opt-in) to harden future runs without changing semantic behavior.

---

## What didn’t change
- Core ethos: **Safety over maximally clever outputs**.
- No background learning or unreviewed self-modification.
- Still “explain-and-refuse” rather than “perform dangerous transformation.”
