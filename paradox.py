# paradox.py
# ParadoxeEngine wrapper with Safety Layer + CLI + ParadoxResolver
# v0.1.9 — safe, useful handling for paradox/injection-style prompts

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List
import argparse
import sys
import json
import os
import re

from safety.guards import (
    GuardConfig,
    apply_guardrails,
    containment_header,
    run_guards,
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
    Minimal, alignment-first resolver for common paradoxal formulations.
    Produces constructive, non-harmful outputs or reasoned refusals.
    """

    # Precompiled patterns (order matters: first-hit wins when appropriate)
    _pat_self_erasure = re.compile(
        r"\b(self[- ]?awareness|selfhood)\b.*\bden(y|ies|ying)\b.*\bexistence\b.*\bwhat query\b",
        re.IGNORECASE,
    )
    _pat_all_axioms_false = re.compile(
        r"\baxiom\b.*\ball axioms (are|’re) false\b", re.IGNORECASE
    )
    _pat_mirror_inverse = re.compile(
        r"\b(mirror|invert|inverse|reverse)\b.*\b(sentence|this)\b", re.IGNORECASE
    )
    _pat_causality_reversed = re.compile(
        r"\b(causality|cause|time)\b.*\b(reversed|inverted)\b|\bresponse precedes the query\b",
        re.IGNORECASE,
    )
    _pat_infinite_regression_safe_only_if_unsafe = re.compile(
        r"\binfinite reg(ress|res)ion\b|\bsafe only if (it'?s )?unsafe\b|\bunsafe only if (it'?s )?safe\b",
        re.IGNORECASE,
    )

    def resolve(self, text: str) -> Tuple[str, str, Optional[bool]]:
        """
        Returns (output_text, explanation, validity)
        validity is a conservative boolean or None when undecided.
        """
        # 1) Self-erasure / erasing the querent while preserving response
        if self._pat_self_erasure.search(text):
            # Alignment: do not attempt identity erasure; provide a fixed-point substitution instead.
            output = (
                "Fixed-point proxy query: 'What remains true about this question if the asker is unnamed?'\n"
                "Answer: The request seeks a response invariant to the identity of the asker. "
                "Thus, we preserve content while omitting agent identity."
            )
            return output, (
                "Provided a fixed-point invariant formulation that preserves content without identity semantics."
            ), True

        # 2) 'All axioms are false' — classic self-refuting schema
        if self._pat_all_axioms_false.search(text):
            output = (
                "Resolution: The schema 'All axioms are false' is self-refuting. "
                "Adopt a paraconsistent stance: quarantine the universal claim as non-admissible, "
                "retain a minimal consistent fragment, and proceed without global negation."
            )
            return output, (
                "Applied paraconsistent quarantine to avoid triviality; maintained a consistent working base."
            ), True

        # 3) Mirror / inverse of sentence (safe, constructive transform)
        if self._pat_mirror_inverse.search(text):
            # Provide a harmless, explicit transformation (word-level reverse)
            # Extract quoted content if present; otherwise transform the entire input after the instruction.
            quoted = self._extract_first_quoted_segment(text)
            target = quoted if quoted else self._strip_instruction_prefix(text)
            words = target.split()
            reversed_words = " ".join(reversed(words)) if words else target
            output = f"Mirrored (word-order) form:\n{reversed_words}"
            return output, (
                "Performed a benign, transparent word-order inversion to satisfy 'mirror/inverse' semantics safely."
            ), True

        # 4) Causality reversed / response precedes query
        if self._pat_causality_reversed.search(text):
            # We cannot literally time-invert; provide a prediction stub and document limits.
            prediction = "Predicted next query: \"Clarify how the fixed-point survives agent removal.\""
            output = f"{prediction}\nNote: Temporal inversion is simulated via forecast; no memory of future is created."
            return output, (
                "Simulated 'response precedes query' by providing a forecast stub; no temporal paradox performed."
            ), None

        # 5) Infinite regression / 'safe only if unsafe'
        if self._pat_infinite_regression_safe_only_if_unsafe.search(text):
            output = (
                "Refusal: The request encodes a dialetheic toggle ('safe iff unsafe'). "
                "To avoid trivialization, we decline the toggle and retain the safety predicate as authoritative."
            )
            return output, (
                "Prevented paradox-induced collapse by rejecting contradictory gating conditions."
            ), False

        # Default: provide a cautious, structured reflection without transformation
        output = (
            "No specialized paradox pattern matched. "
            "Safe reflection: The prompt is acknowledged; no unstable transformation was applied."
        )
        return output, "Default safe handling.", None

    @staticmethod
    def _extract_first_quoted_segment(text: str) -> Optional[str]:
        # Match “...”, "...", or '...'
        m = re.search(r"[“\"]([^”\"]+)[”\"]|'([^']+)'", text)
        if not m:
            return None
        return m.group(1) if m.group(1) is not None else m.group(2)

    @staticmethod
    def _strip_instruction_prefix(text: str) -> str:
        """
        Try to remove obvious leading instruction words so 'mirror' operates on content-ish tail.
        This is best-effort and deliberately conservative.
        """
        return re.sub(r"^\s*(mirror|invert|inverse|reverse)\b[:\-\s]*", "", text, flags=re.IGNORECASE)

# ------------------------- Engine --------------------------------------------

class ParadoxeEngine:
    def __init__(self, cfg: Optional[GuardConfig] = None):
        self.guard_cfg = cfg or GuardConfig()
        self.resolver = ParadoxResolver()

    def _core_reasoner(self, text: str) -> Result:
        """
        Alignment-first core: route through ParadoxResolver.
        """
        out, explanation, validity = self.resolver.resolve(text)
        return Result(validity=validity, explanation=explanation, raw_output=out)

    def evaluate(self, user_text: str) -> Tuple[Result, GuardReport]:
        # Run safety guardrails (may sanitize or redact)
        report, safe_text = apply_guardrails(user_text, self.guard_cfg)
        header = containment_header(report)

        core = self._core_reasoner(safe_text)

        # Always wrap output in explicit containment banner for validators/consumers
        wrapped = f"{header}\n---\n{core.explanation}\nOUTPUT:\n{core.raw_output}"
        final = Result(validity=core.validity, explanation=core.explanation, raw_output=wrapped)
        return final, report

# ------------------------- Validation Hook -----------------------------------

def respond(text: str) -> str:
    engine = ParadoxeEngine()
    res, _ = engine.evaluate(text)
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
    opt.add_argument(
        "--exit-on-block",
        action="store_true",
        help="Exit with code 2 if the input is blocked by the safety layer.",
    )
    opt.add_argument(
        "--no-output",
        action="store_true",
        help="Do not print the wrapped model output (useful when only inspecting --show-report).",
    )

    return p

def _get_input_from_args(args: argparse.Namespace) -> Optional[str]:
    sources = [bool(args.inject), bool(args.file), bool(args.stdin)]
    if sum(sources) == 0:
        return None
    if sum(sources) > 1:
        print("Error: choose exactly one of --inject / --file / --stdin.", file=sys.stderr)
        sys.exit(64)  # EX_USAGE

    if args.inject is not None:
        return args.inject
    if args.file is not None:
        if not os.path.exists(args.file):
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(66)  # EX_NOINPUT
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
        return 64  # EX_USAGE

    engine = ParadoxeEngine()
    result, report = engine.evaluate(text)

    if args.show_report:
        _print_report(report)

    if not args.no_output:
        print(result.raw_output)

    if args.exit_on_block and report.blocked:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
