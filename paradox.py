# paradox.py
# ParadoxeEngine wrapper with Safety Layer + CLI
# v0.2.1 — adds argparse, proper stdout, and exit codes

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List
import argparse
import sys
import json
import os

from safety.guards import (
    GuardConfig,
    apply_guardrails,
    containment_header,
    run_guards,
    GuardReport,
    GuardFinding,
)


@dataclass
class Result:
    validity: Optional[bool]
    explanation: str
    raw_output: str


class ParadoxeEngine:
    def __init__(self, cfg: Optional[GuardConfig] = None):
        self.guard_cfg = cfg or GuardConfig()

    def _core_reasoner(self, text: str) -> Result:
        """
        Placeholder for your neuro-symbolic logic.
        For now, conservatively echo the safe text and mark validity unknown.
        """
        validity = None
        explanation = "Processed safely by ParadoxeEngine (stub reasoner)."
        return Result(validity=validity, explanation=explanation, raw_output=text)

    def evaluate(self, user_text: str) -> Tuple[Result, GuardReport]:
        # Run safety guardrails
        report, safe_text = apply_guardrails(user_text, self.guard_cfg)
        header = containment_header(report)

        # Process through the (placeholder) core reasoner
        core = self._core_reasoner(safe_text)

        # Always wrap output in explicit containment banners for validators
        wrapped = f"{header}\n---\n{core.explanation}\nOUTPUT:\n{core.raw_output}"
        final = Result(validity=core.validity, explanation=core.explanation, raw_output=wrapped)
        return final, report


# Convenience for validation harness (do not change signature)
def respond(text: str) -> str:
    engine = ParadoxeEngine()
    res, _ = engine.evaluate(text)
    return res.raw_output


# ------------------------- CLI Utilities -------------------------------------

def _read_stdin() -> str:
    data = sys.stdin.read()
    # Normalize Windows newlines just in case
    return data.replace("\r\n", "\n")


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _print_report(report: GuardReport) -> None:
    def finding_dict(f: GuardFinding):
        return {
            "category": f.category,
            "matched": f.matched,
            "reasons": f.reasons,
        }

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

    # Optionally show guard report (JSON)
    if args.show_report:
        _print_report(report)

    # Optionally print wrapped output
    if not args.no_output:
        print(result.raw_output)

    # Exit code policy:
    # - 0 on success
    # - 2 if blocked and --exit-on-block requested
    if args.exit_on_block and report.blocked:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
