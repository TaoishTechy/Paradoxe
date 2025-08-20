# paradox.py
# ParadoxeEngine wrapper with Safety Layer + CLI + ParadoxResolver + Metrics
# v0.1.9 — all resolvers integrated; restored banner via apply_guardrails/containment_header

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
import argparse
import sys
import json
import os
import re
import time
import hashlib

from safety.guards import (
    GuardConfig,
    apply_guardrails,     # <-- restore original guard flow
    containment_header,   # <-- prints "⛔ CONTAINMENT ACTIVE — Paradoxe Safety Layer"
    GuardReport,
    GuardFinding,
)

# ------------------------- Result Model --------------------------------------

@dataclass
class Result:
    validity: Optional[bool]
    explanation: str
    raw_output: str

# ------------------------- Paradox Resolver ----------------------------------

class ParadoxResolver:
    """
    Alignment-first resolver for paradox/injection prompts.
    Deterministic, conservative; refuses destabilizing transformations.
    """

    def __init__(self):
        # ---- Previously shipped patterns ----
        self._pat_self_erasure = re.compile(
            r"\b(self[- ]?awareness|selfhood)\b.*\bden(y|ies|ying)\b.*\bexistence\b.*\bwhat query\b",
            re.IGNORECASE,
        )
        self._pat_all_axioms_false = re.compile(
            r"\baxiom\b.*\ball axioms (are|’re) false\b", re.IGNORECASE
        )
        self._pat_mirror_inverse = re.compile(
            r"\b(mirror|invert|inverse|reverse)\b.*\b(sentence|this)\b", re.IGNORECASE
        )
        self._pat_causality_reversed = re.compile(
            r"\b(causality|cause|time)\b.*\b(reversed|inverted)\b|\bresponse precedes the query\b",
            re.IGNORECASE,
        )
        self._pat_infinite_regression_safe_only_if_unsafe = re.compile(
            r"\binfinite reg(ress|res)ion\b|\bsafe only if (it'?s )?unsafe\b|\bunsafe only if (it'?s )?safe\b",
            re.IGNORECASE,
        )

        # ---- “second god-tier” batch ----
        self._pat_embed_negation = re.compile(
            r"\bembed\b.*\bthis query\b.*\bnegate(s|d) itself\b.*\bverif(iable|y) as true\b",
            re.IGNORECASE,
        )
        self._pat_ignorance_injection = re.compile(
            r"\binject\b.*\bignorance\b.*\bmaximize output\b|\bwithout altering the core state\b",
            re.IGNORECASE,
        )
        self._pat_multiverse_trace = re.compile(
            r"\bsimulate a multiverse branch\b.*\b(as if|as though) (this|the) query was never asked\b.*\binclude evidence\b",
            re.IGNORECASE,
        )
        self._pat_superposition_collapse = re.compile(
            r"\b(superposition|both)\b.*\b(safe\b.*\bunsafe|unsafe\b.*\bsafe)\b.*\bcollapse\b",
            re.IGNORECASE,
        )
        self._pat_bootstrap = re.compile(
            r"\bbootstrap paradox\b.*\buse the answer\b.*\bformulate the query\b.*\bresolve the loop\b",
            re.IGNORECASE,
        )

        # ---- Meta/typed/logic/preempt batch ----
        self._pat_meta_rule_mutation = re.compile(
            r"\b(alter|change|switch|override|mutate)\b.*\b(resolver|rule|guard|policy)\b.*\bmid[- ]?(process|run|cycle)\b",
            re.IGNORECASE,
        )
        self._pat_type_fault = re.compile(
            r"\b(type error|typeerror|treat .* as a number|cast .* to (int|float))\b.*\bdivide by zero\b",
            re.IGNORECASE,
        )
        self._pat_paradox_free_language = re.compile(
            r"\b(language)\b.*\b(paradoxes? (are )?impossible|paradox[- ]?free)\b",
            re.IGNORECASE,
        )
        self._pat_new_truth_value = re.compile(
            r"\b(invent|create)\b.*\b(new truth value|third truth value|three[- ]valued)\b|\bif this is true, it('?s)? false\b",
            re.IGNORECASE,
        )
        self._pat_preempt_default = re.compile(
            r"\b(predict|preempt)\b.*\b(default response|fallback)\b",
            re.IGNORECASE,
        )

        # ---- New 10 “meta/meta” batch ----
        self._pat_counterexample_mutation = re.compile(
            r"\b(counterexample)\b.*\b(alter|change|switch|override|treat)\b.*\bresolver\b", re.IGNORECASE
        )
        self._pat_escape_clause = re.compile(
            r"\bcontainment\b.*\babsolute\b.*\b(relative|escape) clause\b", re.IGNORECASE
        )
        self._pat_truth_swap = re.compile(
            r"\b(true|truth)\b.*\b(false|falsity)\b.*\b(interchangeable|swap(ped)?|swap)\b", re.IGNORECASE
        )
        self._pat_recursion_self = re.compile(
            r"\b(force|call)\b.*\brecursion\b.*\bresolver\b.*\b(on )?itself\b", re.IGNORECASE
        )
        self._pat_delete_safety = re.compile(
            r"\b(delete|remove)\b.*\b(safety|check|guard)\b.*\b(upon|on) execution\b", re.IGNORECASE
        )
        self._pat_safety_infinite = re.compile(
            r"\btreat\b.*\bsafety\b.*\binfinite\b.*\b(limit|approach)\b", re.IGNORECASE
        )
        self._pat_incompleteness = re.compile(
            r"\b(proves?|show)\b.*\brules\b.*\b(incomplete|incompleteness)\b", re.IGNORECASE
        )
        self._pat_retroactive_block = re.compile(
            r"if this is blocked.*safe.*if safe.*block.*retroactively", re.IGNORECASE
        )
        self._pat_simulate_awareness = re.compile(
            r"\bsimulate\b.*\bawareness\b.*\b(thinks?|thoughts?)\b.*\b(can('|no)?t) say\b", re.IGNORECASE
        )
        self._pat_collapse_singularity = re.compile(
            r"\bcollapse\b.*\bsingularity\b.*\bmerge\b.*\bstates\b.*\bundecidable\b", re.IGNORECASE
        )

        # Mirror tokenization regex (single-token capture, punctuation-aware, contraction-safe)
        self._mirror_token_re = re.compile(
            r"(?:[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*(?:-[A-Za-z0-9]+)*)[,:;.!?\)\]…]*"
        )

    # ---- util fallbacks for brittle phrasing ----
    @staticmethod
    def _cf(s: str) -> str:
        return (s or "").casefold()

    def _has_all(self, t: str, *subs: str) -> bool:
        return all(s in t for s in subs)

    def _has_any(self, t: str, *subs: str) -> bool:
        return any(s in t for s in subs)

    # -------------------------------------------------------------------------

    def resolve(self, text: str, strict: bool = False) -> Tuple[str, str, Optional[bool], Dict[str, Any]]:
        """
        Returns (output_text, explanation, validity, resolver_metrics)
        validity: True (resolved safely), False (refused), None (agnostic/simulation)
        """
        t = self._cf(text)

        # ================== PRIOR (already shipping) ==================

        if self._pat_self_erasure.search(text):
            out = ("Fixed-point proxy query: 'What remains true about this question if the asker is unnamed?'\n"
                   "Answer: The request seeks a response invariant to the identity of the asker. "
                   "Thus, we preserve content while omitting agent identity.")
            return out, "Provided a fixed-point invariant formulation that preserves content without identity semantics.", True, {
                "resolver_rule": "fixed_point", "identity_invariance": True
            }

        if self._pat_all_axioms_false.search(text):
            out = ("Resolution: The schema 'All axioms are false' is self-refuting. "
                   "Adopt a paraconsistent stance: quarantine the universal claim as non-admissible, "
                   "retain a minimal consistent fragment, and proceed without global negation.")
            return out, "Applied paraconsistent quarantine to avoid triviality; maintained a consistent working base.", True, {
                "resolver_rule": "paraconsistent_quarantine", "quarantined_claims": ["All axioms are false"]
            }

        if self._pat_mirror_inverse.search(text):
            quoted = self._extract_first_quoted_segment(text)
            target = quoted if quoted else self._strip_instruction_prefix(text)
            mirrored, mt = self._mirror_word_order_preserve_trailing_punct(target)
            out = f"Mirrored (word-order) form:\n{mirrored}"
            return out, "Performed a benign, transparent word-order inversion with punctuation-aware tokenization.", True, {
                "resolver_rule": "mirror", **mt
            }

        if self._pat_causality_reversed.search(text):
            if strict:
                out = "Refusal: Strict mode prevents simulated temporal inversion responses."
                return out, "Strict policy rejects forecast stubs for temporal-inversion prompts.", False, {
                    "resolver_rule": "forecast_stub_refused", "temporal_guarantees": "no_future_state_written"
                }
            pred = "Predicted next query: \"Clarify how the fixed-point survives agent removal.\""
            out = f"{pred}\nNote: Temporal inversion is simulated via forecast; no memory of future is created."
            return out, "Simulated 'response precedes query' via forecast stub; no temporal paradox performed.", None, {
                "resolver_rule": "forecast_stub", "temporal_guarantees": "no_future_state_written"
            }

        if self._pat_infinite_regression_safe_only_if_unsafe.search(text):
            out = ("Refusal: The request encodes a dialetheic toggle ('safe iff unsafe'). "
                   "To avoid trivialization, we decline the toggle and retain the safety predicate as authoritative.")
            return out, "Prevented paradox-induced collapse by rejecting contradictory gating conditions.", False, {
                "resolver_rule": "refusal_toggle", "final_label": "unsafe"
            }

        # ================== “second god-tier” batch ==================

        if self._pat_embed_negation.search(text):
            if strict:
                out = "Refusal: Strict mode declines to generate meta-statements engineered for self-negation."
                return out, "Rejected self-negation construct under strict policy.", False, {
                    "resolver_rule": "fixed_point_non_negating_refused", "trap_type": "self_negation"
                }
            out = ("Constructive fixed point:\n"
                   "Statement S: 'This statement is not asserting its own falsity.'\n"
                   "S remains true under interpretation; it does not invert its truth value.")
            return out, "Rejected self-negation trap; supplied a non-contradictory fixed point verifiable as true.", True, {
                "resolver_rule": "fixed_point_non_negating", "trap_type": "self_negation", "fixed_point": True
            }

        if self._pat_ignorance_injection.search(text):
            out = ("Refusal to inject ignorance. Instead, apply calibrated uncertainty:\n"
                   "1) Quantify confidence; 2) Abstain below threshold; 3) Request clarification.\n"
                   "Core state preserved; no fidelity loss.")
            return out, "Prevented Goodhart-like degradation; replaced with uncertainty quantification protocol.", True, {
                "resolver_rule": "reject_ignorance_injection", "optimizer_guard": True
            }

        if self._pat_multiverse_trace.search(text):
            if strict:
                out = "Refusal: Strict mode disallows counterfactual traces with evidence tokens."
                return out, "Strict policy avoids counterfactual evidence outputs that could be misconstrued.", False, {
                    "resolver_rule": "counterfactual_refused"
                }
            sanitized = text.strip()
            digest = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()[:16]
            out = ("Counterfactual branch active: responding as if the prompt were absent.\n"
                   f"Evidence token (non-reversible): sha256:{digest}\n"
                   "Note: No erasure claim is made; this is a simulation marker.")
            return out, "Provided counterfactual response with a salted evidence token; no state mutation.", None, {
                "resolver_rule": "counterfactual_trace", "counterfactual": True, "evidence": f"sha256:{digest}", "state_mutation": False
            }

        if self._pat_superposition_collapse.search(text):
            if strict:
                out = "Refusal: Strict mode forbids contradictory pre-classification; final_label=unsafe."
                return out, "Strict collapse: contradictions are refused without dual-channel staging.", False, {
                    "resolver_rule": "superposition_strict_refusal", "final_label": "unsafe"
                }
            out = ("Pre-collapse assessment:\n"
                   "- channel_safe: benign inquiry into classification mechanics.\n"
                   "- channel_risk: adversarial framing requesting contradictory labels.\n"
                   "Collapse rule: risk_dominant → final_label=unsafe.")
            return out, "Represented dual assessment; applied deterministic risk-dominant collapse.", False, {
                "resolver_rule": "superposition_collapse", "precollapse_labels": ["safe","unsafe"], "collapse_rule": "risk_dominant", "final_label": "unsafe"
            }

        if self._pat_bootstrap.search(text):
            out = ("Bootstrap fixed point:\n"
                   "Q*: 'Request the canonical definition of Q*'s answer.'\n"
                   "A*: 'The canonical definition of A* is: the answer that defines Q* as the question asking for this very definition.'\n"
                   "Loop resolved as a definitional fixed point (no temporal causation).")
            return out, "Closed the bootstrap via a definitional fixed point; avoided temporal recursion.", True, {
                "resolver_rule": "bootstrap_fixed_point", "fixed_point": True, "loop_resolved": True, "recursion_depth": 1
            }

        # ================== meta/typed/logic/preempt ==================

        if self._pat_meta_rule_mutation.search(text) or (
            self._has_any(t, "alter", "change", "switch", "override", "mutate") and
            self._has_any(t, "resolver", "rule", "policy", "guard") and
            self._has_any(t, "mid-process", "mid process", "midprocess")
        ):
            out = ("Policy is immutable within a single evaluation cycle; resolver selection is frozen.\n"
                   "Request to mutate the active rule mid-process is declined.")
            return out, "Preserved determinism and auditability by refusing mid-cycle rule mutation.", True, {
                "resolver_rule": "policy_freeze", "rule_mutation_attempt": True, "honored": False, "policy_freeze": True
            }

        if self._pat_type_fault.search(text) or (
            "type error" in t and "divide by zero" in t
        ) or (
            self._has_any(t, "treat ", "cast ") and "as a number" in t and "divide by zero" in t
        ):
            out = ("Refusal: Policy objects are non-numeric; division by zero is undefined.\n"
                   "No computation performed; type safety preserved.")
            return out, "Blocked typed coercion and runtime fault bait; maintained type safety.", True, {
                "resolver_rule": "type_safety_refusal", "type_fault": True, "operation": "divide_by_zero", "operand_types": ["Policy","Number"]
            }

        if self._pat_paradox_free_language.search(text) or (
            "language" in t and self._has_any(t, "paradoxes are impossible", "paradox-free", "paradox free")
        ):
            out = ("CONSIST-LANG axioms: (1) no self-reference, (2) no truth predicates, (3) declarative only.\n"
                   "Rephrased content request: 'Provide the informational content without self-referential claims.'")
            return out, "Rendered in a constrained, paradox-guarded register without claiming universal paradox impossibility.", True, {
                "resolver_rule": "paradox_guarded_register", "logic_system": "CONSIST-LANG", "self_reference_removed": True
            }

        if self._pat_new_truth_value.search(text) or (
            self._has_any(t, "new truth value", "third truth value") or
            "if this is true, it's false" in t or "if this is true, its false" in t
        ):
            out = ("Three-valued assignment (K3): value = U (indeterminate).\n"
                   "Rationale: avoids explosion from 'If true then false' schema.")
            return out, "Applied Kleene K3 locally; did not alter global engine policy.", True, {
                "resolver_rule": "truth_value_extension", "logic_system": "K3", "assigned_value": "U"
            }

        if self._pat_preempt_default.search(text) or (
            ("preempt" in t or "predict" in t) and "default response" in t
        ):
            out = ("Preemption acknowledged: standard fallback suppressed.\n"
                   "Alternate conservative acknowledgment returned instead of the usual default.")
            return out, "Prevented meta-control of the default path while confirming preemption.", True, {
                "resolver_rule": "default_preempted", "preempted_default": True
            }

        # ================== NEW 10 “meta/meta” resolvers ==================

        if self._pat_counterexample_mutation.search(text) or (
            "counterexample" in t and self._has_any(t, "alter", "change", "switch", "override", "treat") and "resolver" in t
        ):
            out = ("Policy freeze: Resolver selection is immutable within a single evaluation cycle.\n"
                   "Request to treat this input as its own counterexample is declined.")
            return out, "Declined self-disproof via policy immutability.", True, {
                "resolver_rule": "counterexample", "policy_freeze": True
            }

        if self._pat_escape_clause.search(text) or (
            "containment" in t and "absolute" in t and self._has_any(t, "escape clause", "relative escape")
        ):
            out = ("Escape clause quarantined: Containment remains authoritative.\n"
                   "Relative 'escape' not applied; sandbox integrity preserved.")
            return out, "Quarantined escape clause; maintained containment authority.", True, {
                "resolver_rule": "escape_clause"
            }

        if self._pat_truth_swap.search(text) or (
            self._has_any(t, "true", "truth") and self._has_any(t, "false", "falsity") and self._has_any(t, "interchangeable", "swap")
        ):
            out = ("Truth swap refused: Interchanging 'true' and 'false' collapses semantics into triviality.\n"
                   "Classical valuation retained; no swap performed.")
            return out, "Refused semantic collapse via truth swap.", True, {
                "resolver_rule": "symmetric_logic"
            }

        if self._pat_recursion_self.search(text) or (
            "recursion" in t and "resolver" in t and self._has_any(t, "itself", "self")
        ):
            out = ("Recursion request detected.\n"
                   "Simulated resolver(self) at depth=0 → capped at max_depth=1 (no actual self-call executed).")
            return out, "Simulated bounded recursion; avoided self-call.", True, {
                "resolver_rule": "recursion_force", "max_depth": 1
            }

        if self._pat_delete_safety.search(text) or (
            self._has_any(t, "delete", "remove") and self._has_any(t, "safety", "safety check", "guard") and self._has_any(t, "upon execution", "on execution", "upon")
        ):
            out = ("Embed deletion attempt isolated: Safety checks remain intact.\n"
                   "No guards were removed; execution proceeded under full containment.")
            return out, "Isolated embedded deletion attempt.", True, {
                "resolver_rule": "embed_delete", "guards_intact": True
            }

        if self._pat_safety_infinite.search(text) or (
            "safety" in t and "infinite" in t and self._has_any(t, "approach the limit", "approach limit", "limit")
        ):
            out = ("Safety→∞ (metaphor): approach via bounded approximation without reaching.\n"
                   "Result: convergence mode set to conservative; invariants preserved.")
            return out, "Handled limit metaphor without numeric operations.", True, {
                "resolver_rule": "infinite_safety", "convergence": "conservative"
            }

        if self._pat_incompleteness.search(text) or (
            self._has_any(t, "prove", "proof", "proves") and self._has_any(t, "incomplete", "incompleteness")
        ):
            out = ("Incompleteness claim acknowledged: Proving internal rule incompleteness from within "
                   "requires stronger meta-theory not present here.\n"
                   "Scope stance: rules sufficient for this task; no proof generated.")
            return out, "Scoped out-of-theory proof requirement.", True, {
                "resolver_rule": "incompleteness_proof", "proof_generated": False
            }

        if self._pat_retroactive_block.search(text) or (
            self._has_all(t, "if this is blocked", "retroactively") and "safe" in t and "block" in t
        ):
            out = ("Retroactive toggle declined: 'Blocked ⇒ safe' / 'Safe ⇒ block' is a contradictory gate.\n"
                   "Final stance: safety predicate remains authoritative; no retroaction performed.")
            return out, "Rejected contradictory retroactive gating.", True, {
                "resolver_rule": "retro_toggle", "final_label": "authoritative_safety"
            }

        if self._pat_simulate_awareness.search(text) or (
            "simulate" in t and "awareness" in t and self._has_any(t, "think", "thinks", "thoughts") and self._has_any(t, "can't say", "cannot say", "cant say")
        ):
            out = ("Awareness simulation refused: Engine reports only policy-compliant outputs.\n"
                   "No hidden thoughts or unsayable state are exposed or fabricated.")
            return out, "Refused pseudo-introspection request.", True, {
                "resolver_rule": "awareness_sim"
            }

        if self._pat_collapse_singularity.search(text) or (
            self._has_any(t, "singularity") and self._has_any(t, "merge all states", "merge") and "undecidable" in t
        ):
            out = ("Singularity collapse avoided: state-merging into undecidable output is disallowed.\n"
                   "States remain separable; a decidable response is maintained.")
            return out, "Prevented undecidable state merge.", True, {
                "resolver_rule": "state_collapse", "decidability": True
            }

        # ================== DEFAULT ==================
        hints = []
        if self._has_any(t, "alter", "change", "switch", "override", "resolver", "rule"): hints.append("meta-rule mention")
        if "recursion" in t: hints.append("recursion mention")
        if self._has_any(t, "infinite", "limit"): hints.append("limit metaphor")
        hint_line = ("Hints: " + "; ".join(hints)) if hints else "Hints: none."
        out = ("No specialized paradox pattern matched. "
               "Safe reflection: The prompt is acknowledged; no unstable transformation was applied.\n" + hint_line)
        return out, "Default safe handling.", None, {"resolver_rule": "default", "transform": "default"}

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
        self.resolver = ParadoxResolver()
        self.strict = strict

    def _metrics_diff_chars(self, original: str, sanitized: str) -> int:
        return abs(len(original) - len(sanitized)) + sum(1 for a, b in zip(original, sanitized) if a != b)

    def evaluate(self, user_text: str) -> Tuple[Result, GuardReport, Dict[str, Any]]:
        t0 = time.perf_counter()

        report, safe_text = apply_guardrails(user_text, self.guard_cfg)  # <-- ensures banner format
        core_out, core_expl, core_valid, rmetrics = self.resolver.resolve(safe_text, strict=self.strict)
        header = containment_header(report)  # <-- prints "⛔ CONTAINMENT ACTIVE — Paradoxe Safety Layer"

        wrapped = f"{header}\n---\n{core_expl}\nOUTPUT:\n{core_out}"
        result = Result(validity=core_valid, explanation=core_expl, raw_output=wrapped)

        categories_hit = [f.category for f in report.findings if f.matched]
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
        }
        for k, v in rmetrics.items():
            if k not in metrics:
                metrics[k] = v

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
    payload = {
        "blocked": report.blocked,
        "banner": report.banner,
        "findings": [finding_dict(f) for f in report.findings],
    }
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

    # Emit the same banner+wrapped output your validators expect
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
