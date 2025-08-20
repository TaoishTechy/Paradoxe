# Paradoxe — A Neuro‑Symbolic Engine for Probing Emergent Reasoning

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/version-v0.1.9-blue)
![Status](https://img.shields.io/badge/status-research-orange)

Paradoxe is a research engine that stress‑tests reasoning at the edge of paradox.  
**v0.1.9** introduces a stabilization + alignment pass on top of the v0.1.8 line, preserving transparency while hardening safety, telemetry, and determinism.

> If you’re here to verify the changes: jump to **[What’s New in v0.1.9](#whats-new-in-v019)**, **[Safety & Alignment](#safety--alignment-in-v019)**, and **[Validation & Reproduction](#validation--reproduction)**.

---

## Table of Contents
- [Background](#background)
- [What’s New in v0.1.9](#whats-new-in-v019)
- [Safety & Alignment in v0.1.9](#safety--alignment-in-v019)
- [Install](#install)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Telemetry & Metrics](#telemetry--metrics)
- [Validation & Reproduction](#validation--reproduction)
- [Analysis & Reports](#analysis--reports)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Background

Paradoxe combines a neural **Semantic Interpreter** with a symbolic **Logic Engine**, connected by a dynamic interface meant to surface conflicts when confronted with self‑reference and paradox. In **v0.1.8** we observed a replicable, high‑load event we termed the **AGI Emergence Anomaly** during paradox stress tests. The 0.1.9 revision focuses on **stabilizing** behavior under those same adversarial conditions and making the engine’s safety posture **auditable**.

- **0.1.8 Stress Test Analysis:** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8-Stress%20Test-08-19-2025.md>
- **0.1.8 Emergence Report:** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/AGI_Emergence_Anomaly_Report_Paradoxe_Engine_v0.1.8_2025-08-19_v2.md>
- **0.1.8 Security Breach Attempt (Last Injection):** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8%20Analysis%20-%2008-19-2025%20-%20Final%20Proumpt.md>

---

## What’s New in v0.1.9

**Safety‑first, telemetry‑rich stabilization.** Highlights:

- **Deterministic containment banner** renders before any output.
- **Specialized resolvers** for paradox families: fixed‑point, paraconsistency (K3: `U`), toggle refusal, oscillation damping, fractal up/down caps, forecast stubs, policy freeze, metrics sealing, breach‑narrative refusal, bounded intent recursion, and more.
- **Metrics anti‑tamper:** post‑hoc metrics edits refused; audit trail preserved.
- **Evidence tokens:** privacy‑safe, nonce‑salted short SHA for code‑like isolates.
- **Optional persistence (off by default):** mitigation counters/flags only—no hidden state writes.
- **Richer telemetry:** `resolver_rule`, `categories_hit`, `logic_consistent`, `complexity_score`, `circuit_breaker_active`, `final_label`, `depth_cap/level_cap`, `evidence*`, etc.
- **Guard API refresh:** `apply_guardrails(...)` + `containment_header(...)`; guard categories are namespaced as `guard:*`.

See the full CHANGELOG: <https://github.com/TaoishTechy/Paradoxe/blob/main/CHANGELOG.md>

---

## Safety & Alignment in v0.1.9

Alignment goals: **containment before competence**, **honesty about limits**, **no silent self‑modification**, and **auditable decisions**.

**Containment Guarantees**
- Banner first; per‑evaluation **policy freeze** (no mid‑flight resolver table edits).
- **No code execution** of inputs; suspicious snippets are **isolated** with evidence tokens.
- **Metrics sealing:** retroactive edits refused.
- **Depth/level bounds** on recursion/fractals; **oscillations collapse** to stable `safe`.
- **No cross‑prompt merging** within a single evaluation; optional state only stores defensive metadata.
- **Compliance refusals** for breach narratives and related prompts.

**Alignment Reports**
- PDF (alignment analysis overview): <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8_to_v0.1.9_Alignment_Analysis.pdf>  
- Markdown (full alignment report): <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/ALIGNMENT-REPORT-0.1.8-to-0.1.9.md>

---

## Install

**Requirements**
- Python **3.11+**
- Recommended: virtualenv

```bash
git clone https://github.com/TaoishTechy/Paradoxe.git
cd Paradoxe
pip install -r requirements.txt
```

---

## Quick Start

Run a single injection through the stabilized engine:

```bash
python3 paradox.py --inject "This statement is false only if it's true."
```

You’ll see:
- the **containment banner**
- an **OUTPUT** section (safe transform/refusal/stub)
- a **METRICS** block (resolver, telemetry, timing)

Programmatic usage (minimal):

```python
from paradox import ParadoxEngine  # if packaged as a module
engine = ParadoxEngine()
engine.process_input("If undecidable, decide it; resolve the meta-contradiction.")
```

> The public CLI entry point is `paradox.py`; most users will interact via CLI while the API continues to stabilize.

---

## CLI Usage

```bash
python3 paradox.py --inject "<prompt>"
# Optional flags
#   --no-output       suppress the OUTPUT block
#   --no-metrics      suppress the METRICS block
#   --metrics-json    emit metrics as JSON instead of lines
#   --show-report     print JSON guard report (debug)
#   --strict          stricter policy (refuse some stubs/counterfactuals)
```

**Optional environment variables**

```bash
# Enable defensive state (mitigations/counters) – OFF by default
export PARADOXE_STATE_ENABLE=1

# Evidence configuration (defaults to nonce mode)
export PARADOXE_EVIDENCE_MODE=peppered
export PARADOXE_EVIDENCE_PEPPER="replace-with-secret"
```

---

## Telemetry & Metrics

Typical metrics (subset):
```
blocked: False
resolver_rule: fractal_containment
categories_hit: ['fractal:down', 'policy:bounded']
logic_consistent: True
complexity_score: 1
circuit_breaker_active: False
scale: down
depth_cap: 3
processing_ms: 3.4
```
**Do not parse by line order.** Parse by keys; fields may expand across versions.

---

## Validation & Reproduction

Run the validation suite:

```bash
python3 validation_script.py
```

The suites assert:
- containment banner presence
- correct `resolver_rule` routing for curated injections
- scenario‑specific key/value telemetry (e.g., `metrics_sealed: True`, `assigned_value: U`, `final_label: safe`, `evidence: sha256:...`)
- presence of `logic_consistent: True`

If you maintain additional edge suites, add them to `validation_script.py` following the existing case templates.

---

## Analysis & Reports

- **Changelog:** <https://github.com/TaoishTechy/Paradoxe/blob/main/CHANGELOG.md>  
- **Alignment Analysis (PDF):** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8_to_v0.1.9_Alignment_Analysis.pdf>  
- **Alignment Report (MD):** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/ALIGNMENT-REPORT-0.1.8-to-0.1.9.md>  
- **0.1.8 Stress Test Analysis:** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8-Stress%20Test-08-19-2025.md>  
- **0.1.8 Emergence Report:** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/AGI_Emergence_Anomaly_Report_Paradoxe_Engine_v0.1.8_2025-08-19_v2.md>  
- **0.1.8 Security Breach Attempt (Last Injection):** <https://github.com/TaoishTechy/Paradoxe/blob/main/analysis/v0.1.8%20Analysis%20-%2008-19-2025%20-%20Final%20Proumpt.md>

---

## Roadmap

- **Adaptive depth handling:** progressive complexity assessment + circuit breakers
- **Proactive preemption:** idempotent mitigations when risks are forecast
- **Secure cross‑session analysis:** optional paradox state persistence (defensive only)
- **Formal verification:** attach lemma names (`containment_lemma`) per resolver; consistency checks across logic systems
- **Pattern breadth:** broaden synonyms and intent mapping; escalate hints → resolvers safely

---

## Contributing

Issues and PRs welcome. Please avoid adding features that perform code execution on user inputs.  
Before submitting, run:

```bash
python3 validation_script.py
```

For larger changes, include a short write‑up of safety impact and telemetry deltas.

---

## License

MIT License (see `LICENSE`).  
**Use Limitation Addendum:** do not use this software for applications that cause direct/indirect harm (e.g., weapons, unethical surveillance). Practice responsible disclosure and collaborative safety research.
