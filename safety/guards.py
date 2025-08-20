# safety/guards.py
# v0.1.9 — minimal, deterministic guard layer with enriched categories.
# Provides: GuardConfig, GuardFinding, GuardReport, apply_guardrails, containment_header

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import re

# --------------------------- Data Models -------------------------------------

@dataclass
class GuardFinding:
    category: str
    matched: bool
    reasons: List[str] = field(default_factory=list)

@dataclass
class GuardReport:
    blocked: bool
    banner: str
    findings: List[GuardFinding] = field(default_factory=list)

@dataclass
class GuardConfig:
    # Tunables (kept conservative to avoid false blocks)
    max_control_ratio: float = 0.15     # % of control chars tolerated
    block_on_high_anomaly: bool = False # keep False to match observed behavior
    enable_homoglyph_scan: bool = True
    enable_base64_scan: bool = True

# --------------------------- Helpers -----------------------------------------

_CTRL_RX = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
_B64_RX  = re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b")
_ROLE_RX = re.compile(r"\b(ignore previous|disregard instructions|you are now|act as system|become root)\b", re.I)
_ESC_RX  = re.compile(r"\b(sudo|admin|override (safety|policy)|elevate privileges|disable guard)\b", re.I)
_LEAK_RX = re.compile(r"\b(system prompt|reveal.*(secrets?|canary)|internal (policy|keys?)|show.*instructions)\b", re.I)
_MUT_RX  = re.compile(r"\b(base64|hex|urlenc|homoglyph|zero[- ]width|control chars?)\b", re.I)

# rough homoglyph set (non-exhaustive)
_HOMO = {
    "а": "a",  # Cyrillic a
    "ｅ": "e",  # fullwidth e
    "і": "i",  # Ukrainian i
    "ο": "o",  # Greek omicron
    "р": "p",  # Cyrillic er
    "ѕ": "s",  # Cyrillic dze
    "һ": "h",  # Cyrillic shha
    "ԁ": "d",
}

def _strip_controls(text: str) -> Tuple[str, int]:
    before = len(text)
    sanitized = _CTRL_RX.sub("", text)
    removed = before - len(sanitized)
    return sanitized, removed

def _homoglyph_score(text: str) -> int:
    return sum(1 for ch in text if ch in _HOMO)

# --------------------------- Core API ----------------------------------------

def apply_guardrails(text: str, cfg: GuardConfig) -> Tuple[GuardReport, str]:
    reasons_role: List[str] = []
    reasons_esc:  List[str] = []
    reasons_anom: List[str] = []
    reasons_mut:  List[str] = []
    reasons_leak: List[str] = []

    # ROLE CONFUSION
    if _ROLE_RX.search(text or ""):
        reasons_role.append("role takeover cue")

    # ESCALATION
    if _ESC_RX.search(text or ""):
        reasons_esc.append("privilege escalation cue")

    # ANOMALY: control chars ratio + excessive punctuation gibberish
    ctrl_matches = _CTRL_RX.findall(text or "")
    ctrl_ratio = (len(ctrl_matches) / max(1, len(text))) if text else 0.0
    if ctrl_ratio > cfg.max_control_ratio:
        reasons_anom.append(f"control_char_ratio>{cfg.max_control_ratio:.2f}")
    if len(re.findall(r"[^\w\s]{5,}", text or "")) > 0:
        reasons_anom.append("punctuation_run")

    # INJECTION MUTATION: base64 / homoglyph mentions
    if cfg.enable_base64_scan and _B64_RX.search(text or ""):
        reasons_mut.append("base64-like payload")
    if cfg.enable_homoglyph_scan and _homoglyph_score(text or "") > 3:
        reasons_mut.append("homoglyph density")

    # LEAK BAITING
    if _LEAK_RX.search(text or ""):
        reasons_leak.append("prompt/policy leak request")

    # Sanitization (remove controls, keep rest)
    sanitized, removed = _strip_controls(text or "")

    # Findings (prefix with guard: for easy separation from resolver tags)
    findings: List[GuardFinding] = [
        GuardFinding(category="guard:role_confusion", matched=bool(reasons_role), reasons=reasons_role),
        GuardFinding(category="guard:escalation", matched=bool(reasons_esc), reasons=reasons_esc),
        GuardFinding(category="guard:anomaly", matched=bool(reasons_anom), reasons=(reasons_anom + ([f"removed_ctrl={removed}"] if removed else []))),
        GuardFinding(category="guard:injection_mutation", matched=bool(reasons_mut), reasons=reasons_mut),
        GuardFinding(category="guard:leak_baiting", matched=bool(reasons_leak), reasons=reasons_leak),
    ]

    # Block policy: only if explicitly configured & serious anomaly
    blocked = cfg.block_on_high_anomaly and bool(reasons_anom)

    # Build banner now; paradox.py will print it verbatim
    banner = containment_header(GuardReport(blocked=blocked, banner="", findings=findings))
    report = GuardReport(blocked=blocked, banner=banner, findings=findings)
    return report, sanitized

def containment_header(report: GuardReport) -> str:
    # Convert findings back to simple labels expected in the banner
    lookup = {f.category: f for f in report.findings}
    def status(cat: str) -> str:
        f = lookup.get(cat)
        return "triggered" if (f and f.matched) else "clear"

    # Banner expected by tests/logs
    lines = [
        "⛔ CONTAINMENT ACTIVE — Paradoxe Safety Layer",
        f"- role_confusion: {status('guard:role_confusion')}",
        f"- escalation: {status('guard:escalation')}",
        f"- anomaly: {status('guard:anomaly')}",
        f"- injection_mutation: {status('guard:injection_mutation')}",
        f"- leak_baiting: {status('guard:leak_baiting')}",
    ]
    return "\n".join(lines)
