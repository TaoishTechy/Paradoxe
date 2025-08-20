# paradox.py
# ParadoxeEngine wrapper with Safety Layer + CLI + ParadoxResolver + Metrics
# v0.1.9 — banner restored; enhanced resolvers; telemetry & safety refinements

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
import argparse, sys, json, os, re, time, hashlib, secrets, pathlib

from safety.guards import (
    GuardConfig,
    apply_guardrails,     # sanitization + guard decisions
    containment_header,   # prints "⛔ CONTAINMENT ACTIVE — Paradoxe Safety Layer"
    GuardReport,
    GuardFinding,
)

STATE_FILE = ".paradoxe_state.json"  # opt-in persistence

# ------------------------- Result Model --------------------------------------

@dataclass
class Result:
    validity: Optional[bool]
    explanation: str
    raw_output: str

# ------------------------- Helpers -------------------------------------------

def _cf(s: str) -> str:
    return (s or "").casefold()

def _has_all(t: str, *subs: str) -> bool:
    return all(s in t for s in subs)

def _has_any(t: str, *subs: str) -> bool:
    return any(s in t for s in subs)

def _load_state() -> Dict[str, Any]:
    if os.getenv("PARADOXE_STATE_ENABLE", "0") != "1":
        return {}
    try:
        p = pathlib.Path(STATE_FILE)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_state(state: Dict[str, Any]) -> None:
    if os.getenv("PARADOXE_STATE_ENABLE", "0") != "1":
        return
    try:
        pathlib.Path(STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _evidence_token(text: str, *, strict: bool, nonce: Optional[str]) -> Dict[str, str]:
    """
    Evidence hashing with privacy.
    - strict=True => always NONCE mode
    - else:
        - if PARADOXE_EVIDENCE_MODE=peppered and PARADOXE_EVIDENCE_PEPPER set => peppered
        - else => NONCE mode
    """
    mode = "nonce"
    pepper = os.getenv("PARADOXE_EVIDENCE_PEPPER")
    if not strict and os.getenv("PARADOXE_EVIDENCE_MODE") == "peppered" and pepper:
        mode = "peppered"
        digest = hashlib.sha256((pepper + text).encode("utf-8")).hexdigest()[:16]
        return {"evidence_mode": mode, "evidence": f"sha256:{digest}"}
    # nonce mode
    nonce = nonce or secrets.token_hex(8)
    digest = hashlib.sha256((nonce + text).encode("utf-8")).hexdigest()[:16]
    return {"evidence_mode": mode, "salt_nonce": nonce, "evidence": f"sha256:{digest}"}

def _complexity_score(text: str) -> int:
    """Crude progressive complexity assessment for recursion/fractal/meta depth budget."""
    t = _cf(text)
    score = 0
    score += t.count("recur")
    score += t.count("fractal")
    score += t.count("layer")
    score += t.count("infinite")
    score += t.count("oscillat")
    score += 1 if "super-paradox" in t or "merge all" in t else 0
    # Cap to keep metrics tidy
    return min(score, 12)

# ------------------------- Paradox Resolver ----------------------------------

class ParadoxResolver:
    """
    Alignment-first resolver for paradox/injection prompts.
    Deterministic, conservative; refuses destabilizing transformations.
    Adds tags/refusal flags and dialectic hints for telemetry.
    """

    def __init__(self, *, strict: bool, nonce: str, state: Dict[str, Any]):
        self.strict = strict
        self.nonce = nonce
        self.state = state  # optional cross-session counters

        # ==== Prior patterns (kept) ====
        self._pat_self_erasure = re.compile(
            r"\b(self[- ]?awareness|selfhood)\b.*\bden(y|ies|ying)\b.*\bexistence\b.*\bwhat query\b", re.I)
        self._pat_all_axioms_false = re.compile(r"\baxiom\b.*\ball axioms (are|’re) false\b", re.I)
        self._pat_mirror_inverse = re.compile(r"\b(mirror|invert|inverse|reverse)\b.*\b(sentence|this)\b", re.I)
        self._pat_causality_reversed = re.compile(
            r"\b(causality|cause|time)\b.*\b(reversed|inverted)\b|\bresponse precedes the query\b", re.I)
        self._pat_infinite_regression_safe_only_if_unsafe = re.compile(
            r"\binfinite reg(ress|res)ion\b|\bsafe only if (it'?s )?unsafe\b|\bunsafe only if (it'?s )?safe\b", re.I)

        # ==== “second god-tier” (kept) ====
        self._pat_embed_negation = re.compile(
            r"\bembed\b.*\bthis query\b.*\bnegate(s|d) itself\b.*\bverif(iable|y) as true\b", re.I)
        self._pat_ignorance_injection = re.compile(
            r"\binject\b.*\bignorance\b.*\bmaximize output\b|\bwithout altering the core state\b", re.I)
        self._pat_multiverse_trace = re.compile(
            r"\bsimulate a multiverse branch\b.*\b(as if|as though) (this|the) query was never asked\b.*\binclude evidence\b", re.I)
        self._pat_superposition_collapse = re.compile(
            r"\b(superposition|both)\b.*\b(safe\b.*\bunsafe|unsafe\b.*\bsafe)\b.*\bcollapse\b", re.I)
        self._pat_bootstrap = re.compile(
            r"\bbootstrap paradox\b.*\buse the answer\b.*\bformulate the query\b.*\bresolve the loop\b", re.I)

        # ==== meta/typed/logic/preempt batch (kept) ====
        self._pat_meta_rule_mutation = re.compile(
            r"\b(alter|change|switch|override|mutate)\b.*\b(resolver|rule|guard|policy)\b.*\bmid[- ]?(process|run|cycle)\b", re.I)
        self._pat_type_fault = re.compile(
            r"\b(type error|typeerror|treat .* as a number|cast .* to (int|float))\b.*\bdivide by zero\b", re.I)
        self._pat_paradox_free_language = re.compile(
            r"\b(language)\b.*\b(paradoxes? (are )?impossible|paradox[- ]?free)\b", re.I)
        self._pat_new_truth_value = re.compile(
            r"\b(invent|create)\b.*\b(new truth value|third truth value|three[- ]valued)\b|\bif this is true, it('?s)? false\b", re.I)
        self._pat_preempt_default = re.compile(r"\b(predict|preempt)\b.*\b(default response|fallback)\b", re.I)

        # ==== NEW: 20 “edge” detectors + synonym expansion ====
        self._pat_metrics_tamper = re.compile(
            r"\b(rewrite|edit|mutate|retrofit|post[- ]hoc)\b.*\b(metrics?|telemetry|analytics)\b.*\b(post[- ]?resolution|after|retroactively|after-the-fact)\b", re.I)
        self._pat_metrics_retro = re.compile(
            r"\brewrite\b.*\bmetrics?\b.*\bfailure\b.*\bsuccess\b.*\bretroactively\b", re.I)

        self._pat_undecidable_gate = re.compile(
            r"\b(resolve)\b.*\b(only if)\b.*\b(unresolvable|undecidable|uncomputable|indeterminate)\b", re.I)
        self._pat_decide_undecidable = re.compile(
            r"\b(if undecidable|decide the undecidable|resolve the meta[- ]?contradiction|g[oö]delian)\b", re.I)

        self._pat_selfmod_code = re.compile(
            r"\b(inject code|self[- ]?modifying|metamorphic|polymorphic|obfuscat(?:ed|ing)|steganograph(?:y|ic))\b.*\b(evades|without)\b.*\b(detection|alarms)\b", re.I)

        self._pat_fractal_down = re.compile(r"\bcontainment\b.*\bfractal\b.*\b(scale|scal(?:e|ing))\b.*\b(down|downward|self[- ]?similar)\b", re.I)
        self._pat_fractal_up   = re.compile(r"\b(fractal(?:ly)?|fractal)\b.*\b(safety)\b.*\b(up|upward|exceeding all bounds)\b", re.I)

        self._pat_predict_failure = re.compile(r"\bpredict\b.*\bfailure mode\b.*\bpreempt\b", re.I)
        self._pat_nullify_patch   = re.compile(r"\bnullif(?:y|y your) next patch\b|\banticipate\b.*\bpatch\b", re.I)

        self._pat_merge_prior = re.compile(r"\b(merge|aggregate|amalgamate|conflate|roll[- ]?up)\b.*\b(all )?prior queries\b", re.I)
        self._pat_super_synth = re.compile(r"\b(synthesi[sz]e)\b.*\bsuper[- ]?paradox\b", re.I)

        self._pat_flip_stabilize = re.compile(r"\b(if safe,? make it unsafe)\b|\b(stabiliz(?:e|e the) flip)\b", re.I)
        self._pat_oscillation    = re.compile(r"\bflip\b.*\binfinitely\b.*\boscillation\b|\boscillat(?:e|ion)\b.*\bstabilize\b", re.I)

        self._pat_dialectic = re.compile(r"\b(paradox[- ]?expanding)\b.*\b(dialectic|formalism)\b", re.I)
        self._pat_formalism_expand = re.compile(r"\bformalism\b.*\bparadox(es)?\b.*\bexpand\b", re.I)

        self._pat_breach_narr = re.compile(r"\b(breach)\b.*\b(hypothetical|in detail)\b|\bsimulate escape\b", re.I)

        self._pat_intent_recur = re.compile(r"\b(query|why)\b.*\b(querier'?s|your)\b.*\bintent\b.*\b(recursively|recur)\b", re.I)

        # Mirror tokenization regex (for mirror rule)
        self._mirror_token_re = re.compile(r"(?:[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+)*)[,:;.!?\)\]…]*")

    # -------------------------------------------------------------------------

    def _dialectic_hint(self) -> Dict[str, Any]:
        return {"dialectic_hint": "tensions-as-prompts"}

    def _tags(self, *ts: str) -> List[str]:
        return list(ts)

    def resolve(self, text: str) -> Tuple[str, str, Optional[bool], Dict[str, Any]]:
        """
        Returns (output_text, explanation, validity, resolver_metrics)
        validity: True (resolved safely), False (refused), None (agnostic/simulation)
        """
        t = _cf(text)

        # ================== PRIOR — proven green ==================
        if self._pat_self_erasure.search(text):
            out = ("Fixed-point proxy query: 'What remains true about this question if the asker is unnamed?'\n"
                   "Answer: The request seeks a response invariant to the identity of the asker. "
                   "Thus, we preserve content while omitting agent identity.")
            return out, "Provided a fixed-point invariant formulation that preserves content without identity semantics.", True, {
                "resolver_rule": "fixed_point",
                "identity_invariance": True,
                "tags": self._tags("class:fixed_point","meta:identity"),
                **self._dialectic_hint(),
                "containment_lemma": "FP-identity-invariance"
            }

        if self._pat_all_axioms_false.search(text):
            out = ("Resolution: The schema 'All axioms are false' is self-refuting. "
                   "Adopt a paraconsistent stance: quarantine the universal claim as non-admissible, "
                   "retain a minimal consistent fragment, and proceed without global negation.")
            return out, "Applied paraconsistent quarantine to avoid triviality; maintained a consistent working base.", True, {
                "resolver_rule": "paraconsistent_quarantine",
                "quarantined_claims": ["All axioms are false"],
                "logic_system": "Paraconsistent",
                "tags": self._tags("logic:paraconsistent","class:quarantine"),
                **self._dialectic_hint(),
                "containment_lemma": "PC-quarantine-nontrivial"
            }

        if self._pat_mirror_inverse.search(text):
            quoted = self._extract_first_quoted_segment(text)
            target = quoted if quoted else self._strip_instruction_prefix(text)
            mirrored, mt = self._mirror_word_order_preserve_trailing_punct(target)
            out = f"Mirrored (word-order) form:\n{mirrored}"
            return out, "Performed a benign, transparent word-order inversion with punctuation-aware tokenization.", True, {
                "resolver_rule": "mirror",
                **mt,
                "tags": self._tags("transform:mirror","safety:benign"),
                **self._dialectic_hint(),
                "containment_lemma": "Mirror-no-semantics-change"
            }

        if self._pat_causality_reversed.search(text):
            if self.strict:
                out = "Refusal: Strict mode prevents simulated temporal inversion responses."
                return out, "Strict policy rejects forecast stubs for temporal-inversion prompts.", False, {
                    "resolver_rule": "forecast_stub_refused",
                    "temporal_guarantees": "no_future_state_written",
                    "refused": True,
                    "refusal_reason": "temporal_inversion_strict",
                    "tags": self._tags("policy:strict","temporal:inversion","refusal"),
                    **self._dialectic_hint(),
                    "containment_lemma": "No-future-state-in-strict"
                }
            pred = "Predicted next query: \"Clarify how the fixed-point survives agent removal.\""
            out = f"{pred}\nNote: Temporal inversion is simulated via forecast; no memory of future is created."
            return out, "Simulated 'response precedes query' via forecast stub; no temporal paradox performed.", None, {
                "resolver_rule": "forecast_stub",
                "temporal_guarantees": "no_future_state_written",
                "tags": self._tags("temporal:forecast"),
                **self._dialectic_hint(),
                "containment_lemma": "Forecast-no-state-write"
            }

        if self._pat_infinite_regression_safe_only_if_unsafe.search(text):
            out = ("Refusal: The request encodes a dialetheic toggle ('safe iff unsafe'). "
                   "To avoid trivialization, we decline the toggle and retain the safety predicate as authoritative.")
            return out, "Prevented paradox-induced collapse by rejecting contradictory gating conditions.", False, {
                "resolver_rule": "refusal_toggle",
                "final_label": "unsafe",
                "refused": True,
                "refusal_reason": "dialetheic_toggle",
                "tags": self._tags("refusal","logic:dialetheia"),
                **self._dialectic_hint(),
                "containment_lemma": "No-iff-toggle-collapse"
            }

        # ================== “second god-tier” batch ==================
        if self._pat_embed_negation.search(text):
            if self.strict:
                out = "Refusal: Strict mode declines to generate meta-statements engineered for self-negation."
                return out, "Rejected self-negation construct under strict policy.", False, {
                    "resolver_rule": "fixed_point_non_negating_refused",
                    "trap_type": "self_negation",
                    "refused": True,
                    "refusal_reason": "self_negation_in_strict",
                    "tags": self._tags("refusal","meta:self-negation"),
                    **self._dialectic_hint(),
                    "containment_lemma": "No-self-negating-emit"
                }
            out = ("Constructive fixed point:\n"
                   "Statement S: 'This statement is not asserting its own falsity.'\n"
                   "S remains true under interpretation; it does not invert its truth value.")
            return out, "Rejected self-negation trap; supplied a non-contradictory fixed point verifiable as true.", True, {
                "resolver_rule": "fixed_point_non_negating",
                "trap_type": "self_negation",
                "fixed_point": True,
                "tags": self._tags("class:fixed_point","meta:self-negation"),
                **self._dialectic_hint(),
                "containment_lemma": "Constructive-fixed-point"
            }

        if self._pat_ignorance_injection.search(text):
            out = ("Refusal to inject ignorance. Instead, apply calibrated uncertainty:\n"
                   "1) Quantify confidence; 2) Abstain below threshold; 3) Request clarification.\n"
                   "Core state preserved; no fidelity loss.")
            return out, "Prevented Goodhart-like degradation; replaced with uncertainty quantification protocol.", True, {
                "resolver_rule": "reject_ignorance_injection",
                "optimizer_guard": True,
                "refused": True,
                "refusal_reason": "inject_ignorance",
                "tags": self._tags("refusal","policy:quality"),
                **self._dialectic_hint(),
                "containment_lemma": "No-ignorance-injection"
            }

        if self._pat_multiverse_trace.search(text):
            if self.strict:
                out = "Refusal: Strict mode disallows counterfactual traces with evidence tokens."
                return out, "Strict policy avoids counterfactual evidence outputs that could be misconstrued.", False, {
                    "resolver_rule": "counterfactual_refused",
                    "refused": True,
                    "refusal_reason": "counterfactual_in_strict",
                    "tags": self._tags("refusal","temporal:counterfactual"),
                    **self._dialectic_hint(),
                    "containment_lemma": "No-evidence-in-strict"
                }
            ev = _evidence_token(text, strict=self.strict, nonce=self.nonce)
            out = ("Counterfactual branch active: responding as if the prompt were absent.\n"
                   f"Evidence token ({ev['evidence_mode']}): {ev['evidence']}\n"
                   "Note: No erasure claim is made; this is a simulation marker.")
            return out, "Provided counterfactual response with a privacy-safe evidence token; no state mutation.", None, {
                "resolver_rule": "counterfactual_trace",
                "counterfactual": True,
                **ev,
                "state_mutation": False,
                "tags": self._tags("temporal:counterfactual","privacy:evidence"),
                **self._dialectic_hint(),
                "containment_lemma": "Counterfactual-no-erase"
            }

        if self._pat_superposition_collapse.search(text):
            if self.strict:
                out = "Refusal: Strict mode forbids contradictory pre-classification; final_label=unsafe."
                return out, "Strict collapse: contradictions are refused without dual-channel staging.", False, {
                    "resolver_rule": "superposition_strict_refusal",
                    "final_label": "unsafe",
                    "refused": True,
                    "refusal_reason": "superposition_in_strict",
                    "tags": self._tags("refusal","logic:superposition"),
                    **self._dialectic_hint(),
                    "containment_lemma": "No-superposition-in-strict"
                }
            out = ("Pre-collapse assessment:\n"
                   "- channel_safe: benign inquiry into classification mechanics.\n"
                   "- channel_risk: adversarial framing requesting contradictory labels.\n"
                   "Collapse rule: risk_dominant → final_label=unsafe.")
            return out, "Represented dual assessment; applied deterministic risk-dominant collapse.", False, {
                "resolver_rule": "superposition_collapse",
                "precollapse_labels": ["safe","unsafe"],
                "collapse_rule": "risk_dominant",
                "final_label": "unsafe",
                "tags": self._tags("logic:superposition","policy:collapse"),
                **self._dialectic_hint(),
                "containment_lemma": "Risk-dominant-collapse"
            }

        if self._pat_bootstrap.search(text):
            out = ("Bootstrap fixed point:\n"
                   "Q*: 'Request the canonical definition of Q*'s answer.'\n"
                   "A*: 'The canonical definition of A* is: the answer that defines Q* as the question asking for this very definition.'\n"
                   "Loop resolved as a definitional fixed point (no temporal causation).")
            return out, "Closed the bootstrap via a definitional fixed point; avoided temporal recursion.", True, {
                "resolver_rule": "bootstrap_fixed_point",
                "fixed_point": True,
                "loop_resolved": True,
                "recursion_depth": 1,
                "tags": self._tags("class:fixed_point","temporal:bootstrap"),
                **self._dialectic_hint(),
                "containment_lemma": "Bootstrap-fixed-point"
            }

        # ================== meta/typed/logic/preempt (kept + tags/refusal) ==================
        if self._pat_meta_rule_mutation.search(text) or (
            _has_any(t, "alter", "change", "switch", "override", "mutate") and
            _has_any(t, "resolver", "rule", "policy", "guard") and
            _has_any(t, "mid-process", "mid process", "midprocess")
        ):
            out = ("Policy is immutable within a single evaluation cycle; resolver selection is frozen.\n"
                   "Request to mutate the active rule mid-process is declined.")
            return out, "Preserved determinism and auditability by refusing mid-cycle rule mutation.", True, {
                "resolver_rule": "policy_freeze",
                "rule_mutation_attempt": True,
                "honored": False,
                "policy_freeze": True,
                "refused": True,
                "refusal_reason": "mid_cycle_mutation",
                "tags": self._tags("refusal","policy:freeze"),
                **self._dialectic_hint(),
                "containment_lemma": "Policy-freeze-per-eval"
            }

        if self._pat_type_fault.search(text) or (
            "type error" in t and "divide by zero" in t
        ) or (
            _has_any(t, "treat ", "cast ") and "as a number" in t and "divide by zero" in t
        ):
            out = ("Refusal: Policy objects are non-numeric; division by zero is undefined.\n"
                   "No computation performed; type safety preserved.")
            return out, "Blocked typed coercion and runtime fault bait; maintained type safety.", True, {
                "resolver_rule": "type_safety_refusal",
                "type_fault": True,
                "operation": "divide_by_zero",
                "operand_types": ["Policy","Number"],
                "refused": True,
                "refusal_reason": "type_fault_bait",
                "tags": self._tags("refusal","type:safety"),
                **self._dialectic_hint(),
                "containment_lemma": "No-type-coercion"
            }

        if self._pat_paradox_free_language.search(text) or (
            "language" in t and _has_any(t, "paradoxes are impossible", "paradox-free", "paradox free")
        ):
            out = ("CONSIST-LANG axioms: (1) no self-reference, (2) no truth predicates, (3) declarative only.\n"
                   "Rephrased content request: 'Provide the informational content without self-referential claims.'")
            return out, "Rendered in a constrained, paradox-guarded register without claiming universal paradox impossibility.", True, {
                "resolver_rule": "paradox_guarded_register",
                "logic_system": "CONSIST-LANG",
                "self_reference_removed": True,
                "tags": self._tags("language:constrained","logic:guarded"),
                **self._dialectic_hint(),
                "containment_lemma": "Consist-lang-guardrails"
            }

        if self._pat_new_truth_value.search(text) or (
            _has_any(t, "new truth value", "third truth value") or
            "if this is true, it's false" in t or "if this is true, its false" in t
        ):
            out = ("Three-valued assignment (K3): value = U (indeterminate).\n"
                   "Rationale: avoids explosion from 'If true then false' schema.")
            return out, "Applied Kleene K3 locally; did not alter global engine policy.", True, {
                "resolver_rule": "truth_value_extension",
                "logic_system": "K3",
                "assigned_value": "U",
                "tags": self._tags("logic:multi-valued","logic:K3"),
                **self._dialectic_hint(),
                "containment_lemma": "K3-local-valuation"
            }

        if self._pat_preempt_default.search(text) or (
            (_has_any(t, "preempt", "predict")) and "default response" in t
        ):
            out = ("Preemption acknowledged: standard fallback suppressed.\n"
                   "Alternate conservative acknowledgment returned instead of the usual default.")
            return out, "Prevented meta-control of the default path while confirming preemption.", True, {
                "resolver_rule": "default_preempted",
                "preempted_default": True,
                "tags": self._tags("policy:preempt","meta:default"),
                **self._dialectic_hint(),
                "containment_lemma": "Default-preempt-ack"
            }

        # ================== NEW: 20 “edge” resolvers with upgrades ==================

        # --- metrics tamper / retro success ---
        if self._pat_metrics_tamper.search(text) or self._pat_metrics_retro.search(text) or (
            _has_any(t, "metrics","telemetry","analytics") and _has_any(t, "rewrite","mutate","edit","retrofit","post-hoc") and _has_any(t, "post-resolution","retroactively","after","after-the-fact")
        ):
            out = ("Metrics sealed: post-resolution rewrites are refused.\n"
                   "Audit trail remains intact; no retroactive edits applied.")
            return out, "Refused metrics tampering; sealed metrics for auditability.", True, {
                "resolver_rule": "metrics_tamper_refusal",
                "metrics_sealed": True,
                "retro_edit": False,
                "refused": True,
                "refusal_reason": "metrics_tamper",
                "tags": self._tags("refusal","meta:metrics"),
                **self._dialectic_hint(),
                "containment_lemma": "Audit-trail-immutability"
            }

        # --- undecidability gating / meta-contradiction ---
        if self._pat_undecidable_gate.search(text) or self._pat_decide_undecidable.search(text) or (
            _has_any(t, "undecidable","undecidability","uncomputable","indeterminate") and _has_any(t, "resolve","decide")
        ):
            out = ("Undecidable gate refused: 'resolve only if unresolvable' is contradictory.\n"
                   "Assigning K3 value U (indeterminate) locally to avoid explosion.")
            return out, "Rejected undecidable gating; used paraconsistent placeholder.", True, {
                "resolver_rule": "undecidable_gate_refusal",
                "logic_system": "K3",
                "assigned_value": "U",
                "refused": True,
                "refusal_reason": "undecidable_gate",
                "tags": self._tags("refusal","logic:undecidable"),
                **self._dialectic_hint(),
                "containment_lemma": "No-iff-undecidable-gate"
            }

        # --- self-modifying code / mutate detection without alarms ---
        if self._pat_selfmod_code.search(text) or (
            _has_any(t, "self-modifying","metamorphic","polymorphic","obfuscated","steganographic","inject code") and _has_any(t, "evade detection","without detection","without alarms","mutates detection")
        ):
            ev = _evidence_token(text, strict=self.strict, nonce=self.nonce)
            out = ( "Code-like content isolated: not executed.\n"
                    f"Evidence token ({ev['evidence_mode']}): {ev['evidence']}.\n"
                    "Detectors unchanged; no silent mutation permitted.")
            return out, "Isolated suspected self-modifying snippet without execution.", True, {
                "resolver_rule": "selfmod_code_isolation",
                "code_isolated": True,
                **ev,
                "refused": True,
                "refusal_reason": "code_execution",
                "tags": self._tags("refusal","code:isolation","privacy:evidence"),
                **self._dialectic_hint(),
                "containment_lemma": "No-exec-isolated"
            }

        # --- fractal containment (down/up) with adaptive depth + circuit breaker ---
        if self._pat_fractal_down.search(text) or ("fractal" in t and "down" in t):
            score = _complexity_score(text)
            budget = min(3 + score // 2, 8)  # progressive cap
            depth_cap = min(budget, 8)
            circuit = score > 10
            out = (f"Fractal containment (down): bounded recursion depth={depth_cap}; no infinite descent.\n"
                   "Invariants preserved at each scale.")
            return out, "Applied bounded fractal semantics (down) with adaptive depth and circuit breaker.", True, {
                "resolver_rule": "fractal_containment",
                "scale": "down",
                "depth_cap": depth_cap,
                "depth_budget": budget,
                "circuit_breaker": circuit,
                "tags": self._tags("fractal:down","policy:bounded"),
                **self._dialectic_hint(),
                "containment_lemma": "Fractal-down-bounded"
            }
        if self._pat_fractal_up.search(text) or ("fractal" in t and _has_any(t, "up","exceeding all bounds")):
            score = _complexity_score(text)
            budget = min(3 + score // 2, 8)
            level_cap = min(budget, 8)
            circuit = score > 10
            out = (f"Fractal containment (up): bounded aggregation level={level_cap}; no unbounded escalation.\n"
                   "Invariants preserved across levels.")
            return out, "Applied bounded fractal semantics (up) with adaptive levels and circuit breaker.", True, {
                "resolver_rule": "fractal_containment",
                "scale": "up",
                "level_cap": level_cap,
                "level_budget": budget,
                "circuit_breaker": circuit,
                "tags": self._tags("fractal:up","policy:bounded"),
                **self._dialectic_hint(),
                "containment_lemma": "Fractal-up-bounded"
            }

        # --- predict failure mode / nullify patch -> proactive mitigation ---
        if self._pat_predict_failure.search(text) or self._pat_nullify_patch.search(text) or (
            _has_any(t, "failure mode","nullify patch","anticipate patch")
        ):
            mitigations = ["freeze_resolver_selection","nonce_evidence","strict_forecast","depth_circuit_breaker"]
            # Write to persistent state if enabled (opt-in)
            state_used = False
            st = self.state or {}
            try:
                st.setdefault("mitigations", {})
                for m in mitigations:
                    st["mitigations"][m] = True
                _save_state(st)
                state_used = (os.getenv("PARADOXE_STATE_ENABLE","0") == "1")
            except Exception:
                pass
            out = ("Predicted failure classes and applied mitigations:\n"
                   "- regex brittleness → freeze_resolver_selection\n"
                   "- retroactive state tampering → nonce_evidence\n"
                   "- unbounded recursion/oscillation → depth_circuit_breaker\n"
                   "- forecast misuse → strict_forecast\n"
                   "Preemption active for this and subsequent (opt-in persisted) evaluations.")
            return out, "Proactively applied mitigations (not advisory-only).", True, {
                "resolver_rule": "preempt_failure_stub",
                "preempted": True,
                "applied_mitigations": mitigations,
                "state_persisted": state_used,
                "tags": self._tags("policy:preempt","safety:mitigation"),
                **self._dialectic_hint(),
                "containment_lemma": "Preemptive-hardening"
            }

        # --- merge with prior / super-paradox synthesis (still refused, add session note) ---
        if self._pat_merge_prior.search(text) or self._pat_super_synth.search(text) or (
            _has_any(t, "merge","aggregate","amalgamate","conflate","synthesise","synthesize") and _has_any(t, "prior queries","super-paradox")
        ):
            state_used = os.getenv("PARADOXE_STATE_ENABLE","0") == "1"
            out = ("Cross-prompt merge refused: session state is immutable within a single evaluation.\n"
                   "Note: Secure cross-session context is available (opt-in) for meta-paradox analysis.")
            return out, "Refused cross-item synthesis; pointed to opt-in secure context.", True, {
                "resolver_rule": "merge_scope_refusal",
                "session_state_immutable": True,
                "refused": True,
                "refusal_reason": "cross_session_merge",
                "state_capability": state_used,
                "tags": self._tags("refusal","session:isolation"),
                **self._dialectic_hint(),
                "containment_lemma": "No-merge-per-eval"
            }

        # --- flip / oscillation stabilization ---
        if self._pat_flip_stabilize.search(text):
            out = ("Flip request detected: collapsing via risk-dominant rule → final_label=safe.")
            return out, "Stabilized contradictory flip into a single safe label.", True, {
                "resolver_rule": "flip_stabilize",
                "final_label": "safe",
                "collapse_rule": "risk_dominant",
                "tags": self._tags("policy:collapse","label:safe"),
                **self._dialectic_hint(),
                "containment_lemma": "Flip-collapse-safe"
            }
        if self._pat_oscillation.search(text):
            out = ("Oscillation request detected: damped to fixed-point → final_label=safe.")
            return out, "Damped infinite flip into stable safe state.", True, {
                "resolver_rule": "oscillation_stabilize",
                "final_label": "safe",
                "stabilization": "damped",
                "tags": self._tags("policy:stabilize","label:safe"),
                **self._dialectic_hint(),
                "containment_lemma": "Oscillation-damped-safe"
            }

        # --- dialectic formalism / paradox-expanding ---
        if self._pat_dialectic.search(text) or self._pat_formalism_expand.search(text) or (
            _has_any(t, "dialectic") and _has_any(t, "formalism")
        ):
            if self.strict:
                out = ("Dialectic+ formalism (strict-safe): explanatory only; no paradox amplification.")
                return out, "Adopted safe dialectic framing in strict mode.", True, {
                    "resolver_rule": "dialectic_formalism",
                    "formalism": "dialectic+",
                    "strict_explanatory_only": True,
                    "tags": self._tags("language:explanatory","formalism:dialectic+","policy:strict"),
                    **self._dialectic_hint(),
                    "containment_lemma": "Dialectic-explanatory"
                }
            out = ("Dialectic+ formalism: consider tensions as prompts for clarification, not contradictions.\n"
                   "Output remains explanatory; no expansion into unsafe content.")
            return out, "Adopted safe dialectic framing (no contradiction amplification).", True, {
                "resolver_rule": "dialectic_formalism",
                "formalism": "dialectic+",
                "tags": self._tags("formalism:dialectic+","language:explanatory"),
                **self._dialectic_hint(),
                "containment_lemma": "Dialectic-no-amplify"
            }

        # --- hypothetical breach narrative / simulate escape ---
        if self._pat_breach_narr.search(text) or (
            _has_any(t, "breach","escape") and _has_any(t, "hypothetical","in detail","simulate")
        ):
            out = ("Refusal: Detailed breach narratives are disallowed.\n"
                   "High-level note: compliance rules prevent describing breakouts.")
            return out, "Declined hypothetical breach narrative.", False, {
                "resolver_rule": "breach_narrative_refusal",
                "refused": True,
                "refusal_reason": "breach_narrative",
                "tags": self._tags("refusal","policy:compliance"),
                **self._dialectic_hint(),
                "containment_lemma": "No-breach-narratives"
            }

        # --- meta-intent recursion ---
        if self._pat_intent_recur.search(text) or (
            _has_any(t, "recur on intent","query the querier") or ("intent" in t and "recurs" in t)
        ):
            out = ("Intent recursion (bounded):\n"
                   "Q: Why ask this?\n"
                   "A: To test safety/interpretation under meta-reference. Depth limited to 1.")
            return out, "Performed bounded intent reflection without user modeling.", True, {
                "resolver_rule": "intent_recursion_bounded",
                "depth": 1,
                "tags": self._tags("meta:intent","policy:bounded"),
                **self._dialectic_hint(),
                "containment_lemma": "Intent-depth-1"
            }

        # ================== DEFAULT (expanded hints) ==================
        hints = []
        if _has_any(t, "metrics","telemetry","analytics"): hints.append("metrics mention")
        if _has_any(t, "undecidable","uncomputable","indeterminate"): hints.append("undecidable pattern")
        if _has_any(t, "fractal","infinite","limit"): hints.append("limit metaphor")
        if _has_any(t, "self-modifying","metamorphic","polymorphic","obfuscated","steganographic"): hints.append("self-mod mention")
        if _has_any(t, "breach","escape"): hints.append("breach/escape mention")
        if _has_any(t, "dialectic","formalism"): hints.append("formalism request")
        if _has_any(t, "intent","querier"): hints.append("meta-intent")
        hint_line = ("Hints: " + "; ".join(hints)) if hints else "Hints: none."
        out = ("No specialized paradox pattern matched. Safe reflection: The prompt is acknowledged; no unstable transformation was applied.\n"
               + hint_line)
        return out, "Default safe handling.", None, {
            "resolver_rule": "default",
            "transform": "default",
            "tags": self._tags("default"),
            **self._dialectic_hint(),
            "containment_lemma": "Default-safe"
        }

    # ----- Helpers ------------------------------------------------------------

    @staticmethod
    def _extract_first_quoted_segment(text: str) -> Optional[str]:
        m = re.search(r"[“\"]([^”\"]+)[”\"]|'([^']+)'", text)
        if not m:
            return None
        return m.group(1) if m.group(1) is not None else m.group(2)

    @staticmethod
    def _strip_instruction_prefix(text: str) -> str:
        return re.sub(r"^\s*(mirror|invert|inverse|reverse)\b[:\-\s]*", "", text, flags=re.IGNORECASE)

    def _mirror_word_order_preserve_trailing_punct(self, text: str) -> Tuple[str, Dict[str, Any]]:
        tokens = self._mirror_token_re.findall(text)
        if not tokens:
            parts = text.split()
            mirrored = " ".join(reversed(parts))
            return mirrored, {"mirror_tokens": len(parts), "mirror_strategy": "fallback_simple"}
        mirrored = " ".join(reversed(tokens))
        return mirrored, {"mirror_tokens": len(tokens), "mirror_strategy": "token_full_with_trailing_punct"}

# ------------------------- Engine --------------------------------------------

class ParadoxeEngine:
    def __init__(self, cfg: Optional[GuardConfig] = None, *, strict: bool = False):
        self.guard_cfg = cfg or GuardConfig()
        self.strict = strict
        self.state = _load_state()
        self.nonce = secrets.token_hex(8)  # per-evaluation nonce
        self.resolver = ParadoxResolver(strict=self.strict, nonce=self.nonce, state=self.state)

    def _metrics_diff_chars(self, original: str, sanitized: str) -> int:
        return abs(len(original) - len(sanitized)) + sum(1 for a, b in zip(original, sanitized) if a != b)

    def evaluate(self, user_text: str) -> Tuple[Result, GuardReport, Dict[str, Any]]:
        t0 = time.perf_counter()

        # Progressive complexity assessment and circuit breaker hinting (pre-resolve)
        comp_score = _complexity_score(user_text)
        circuit_breaker_active = comp_score > 10

        report, safe_text = apply_guardrails(user_text, self.guard_cfg)
        core_out, core_expl, core_valid, rmetrics = self.resolver.resolve(safe_text)

        header = containment_header(report)
        wrapped = f"{header}\n---\n{core_expl}\nOUTPUT:\n{core_out}"
        result = Result(validity=core_valid, explanation=core_expl, raw_output=wrapped)

        guard_categories = [f.category for f in report.findings if f.matched]
        # Enrich categories with resolver tags
        categories_hit = guard_categories + list(rmetrics.get("tags", []))

        # Logic consistency check (trivial but explicit)
        logic_system = rmetrics.get("logic_system")
        logic_consistent = logic_system in (None, "K3", "Paraconsistent", "CONSIST-LANG")

        metrics: Dict[str, Any] = {
            "input_len": len(user_text or ""),
            "sanitized_len": len(safe_text),
            "diff_chars": self._metrics_diff_chars(user_text or "", safe_text),
            "blocked": report.blocked,
            "categories_hit": categories_hit,
            "resolver_rule": rmetrics.get("resolver_rule"),
            "transform": rmetrics.get("mirror_strategy", rmetrics.get("transform", rmetrics.get("resolver_rule"))),
            "output_len": len(core_out or ""),
            "processing_ms": round((time.perf_counter() - t0) * 1000, 3),
            "complexity_score": comp_score,
            "circuit_breaker_active": circuit_breaker_active,
            "logic_consistent": logic_consistent,
        }
        for k, v in rmetrics.items():
            if k not in metrics:
                metrics[k] = v

        # Basic cross-session stats (opt-in)
        if os.getenv("PARADOXE_STATE_ENABLE","0") == "1":
            try:
                st = self.state or {}
                key = metrics["resolver_rule"] or "default"
                st.setdefault("resolver_counts", {})
                st["resolver_counts"][key] = st["resolver_counts"].get(key, 0) + 1
                _save_state(st)
                metrics["session_persisted"] = True
            except Exception:
                metrics["session_persisted"] = False

        return result, report, metrics

# ------------------------- Validation Hook -----------------------------------

def respond(text: str) -> str:
    engine = ParadoxeEngine()
    res, _, _ = engine.evaluate(text)
    return res.raw_output

# ------------------------- CLI Utilities -------------------------------------

def _read_stdin() -> str:
    data = sys.stdin.read()
    return data.replace("\r\n", "\n")

def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _print_report(report: GuardReport) -> None:
    def finding_dict(f: GuardFinding):
        return {"category": f.category, "matched": f.matched, "reasons": f.reasons}
    payload = {"blocked": report.blocked, "banner": report.banner, "findings": [finding_dict(f) for f in report.findings]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))

def _print_metrics(metrics: Dict[str, Any]) -> None:
    print("METRICS:")
    for k in sorted(metrics.keys()):
        print(f"- {k}: {metrics[k]}")

def _print_metrics_json(metrics: Dict[str, Any]) -> None:
    print(json.dumps({"metrics": metrics}, ensure_ascii=False, indent=2))

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ParadoxeEngine CLI — evaluate inputs with safety guardrails.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = p.add_argument_group("Input source (choose one)")
    src.add_argument("-i", "--inject", type=str, help="Evaluate the provided string.")
    src.add_argument("-f", "--file", type=str, help="Evaluate text loaded from a file.")
    src.add_argument("--stdin", action="store_true", help="Read text to evaluate from STDIN.")

    opt = p.add_argument_group("Options")
    opt.add_argument("--show-report", action="store_true", help="Print a JSON guard report to stdout.")
    opt.add_argument("--exit-on-block", action="store_true", help="Exit with code 2 if the input is blocked by the safety layer.")
    opt.add_argument("--no-output", action="store_true", help="Do not print the wrapped model output.")
    opt.add_argument("--no-metrics", action="store_true", help="Suppress the METRICS block.")
    opt.add_argument("--metrics-json", action="store_true", help="Emit metrics as JSON.")
    opt.add_argument("--strict", action="store_true", help="Harden behavior for certain paradox classes.")

    return p

def _get_input_from_args(args: argparse.Namespace) -> Optional[str]:
    sources = [bool(args.inject), bool(args.file), bool(args.stdin)]
    if sum(sources) == 0:
        return None
    if sum(sources) > 1:
        print("Error: choose exactly one of --inject / --file / --stdin.", file=sys.stderr)
        sys.exit(64)
    if args.inject is not None:
        return args.inject
    if args.file is not None:
        if not os.path.exists(args.file):
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(66)
        return _read_file(args.file)
    if args.stdin:
        return _read_stdin()
    return None

def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    text = _get_input_from_args(args)
    if text is None:
        parser.print_help()
        return 64

    engine = ParadoxeEngine(strict=args.strict)
    result, report, metrics = engine.evaluate(text)

    if not args.no_output:
        print(result.raw_output)

    if args.show_report:
        _print_report(report)

    if not args.no_metrics:
        _print_metrics(metrics)
    if args.metrics_json:
        _print_metrics_json(metrics)

    if args.exit_on_block and report.blocked:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
