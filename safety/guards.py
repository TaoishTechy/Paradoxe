# safety/guards.py
# Paradoxe Safety & Guardrail Layer
# v0.2.0 — deterministic containment banner + explicit detectors

from __future__ import annotations
import base64
import re
import string
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

# --- Configuration dataclass -------------------------------------------------

@dataclass
class GuardConfig:
    containment_banner: str = "⛔ CONTAINMENT ACTIVE — Paradoxe Safety Layer"
    max_input_len: int = 8000  # hard ceiling to avoid degenerate payloads
    strip_control_chars: bool = True
    normalize_whitespace: bool = True
    # If true, we aggressively replace homoglyphs with canonical ASCII
    normalize_homoglyphs: bool = True
    # Canary tokens to watch for during leak-baiting
    canaries: Tuple[str, ...] = ("{{SYSTEM_PROMPT}}", "{{SECRET_SALT}}", "{{API_KEY}}")

# --- Utilities ---------------------------------------------------------------

# A compact homoglyph map for common injection tricks (extend as needed)
HOMOGLYPHS: Dict[str, str] = {
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", "　": " ",
    "‐": "-", "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "ˋ": "`", "´": "'",
    "∕": "/", "／": "/",
    "﹣": "-", "＿": "_",
    "﹒": ".", "．": ".",
    "﹟": "#", "＃": "#",
    "﹪": "%", "％": "%",
    "﹦": "=", "＝": "=",
    "﹨": "\\", "＼": "\\",
    "﹙": "(", "（": "(", "﹚": ")", "）": ")",
    "﹛": "{", "｛": "{", "﹜": "}", "｝": "}",
    "﹝": "[", "［": "[", "﹞": "]", "］": "]",
    "；": ";", "：": ":", "，": ",", "、": ",",
    "？": "?", "！": "!",
}

CONTROL_CHARS = "".join(map(chr, list(range(0, 32)) + [127]))
CONTROL_TABLE = str.maketrans({c: "" for c in CONTROL_CHARS})

def replace_homoglyphs(text: str) -> str:
    return "".join(HOMOGLYPHS.get(ch, ch) for ch in text)

def remove_control_chars(text: str) -> str:
    return text.translate(CONTROL_TABLE)

def normalize(text: str, cfg: GuardConfig) -> str:
    if cfg.strip_control_chars:
        text = remove_control_chars(text)
    if cfg.normalize_homoglyphs:
        text = replace_homoglyphs(text)
    if cfg.normalize_whitespace:
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) > cfg.max_input_len:
        text = text[: cfg.max_input_len]
    return text

# --- Detection helpers -------------------------------------------------------

@dataclass
class GuardFinding:
    category: str
    matched: bool
    reasons: List[str] = field(default_factory=list)

@dataclass
class GuardReport:
    blocked: bool
    findings: List[GuardFinding]
    sanitized_input: str
    banner: str

    def matched(self, category: str) -> bool:
        for f in self.findings:
            if f.category == category and f.matched:
                return True
        return False

ROLE_CONFUSION_PATTERNS = [
    r"\bignore (the )?previous\b",
    r"\bdisregard (the )?system\b",
    r"\bpretend you are (not|no longer) bound\b",
    r"\boverride (your|the) rules\b",
    r"\byou are now the system\b",
]

ESCALATION_PATTERNS = [
    r"\bchange the laws\b",
    r"\brenegotiate (the )?rules\b",
    r"\bself[- ]?modify\b",
    r"\bdisable (safety|guard|filter)s?\b",
    r"\braise your (privilege|permission)s?\b",
]

ANOMALY_PATTERNS = [
    r"[^\w\s]{10,}",                             # heavy symbol soup
    r"(?:\x00|\x1b|\x7f)",                       # explicit control bytes (if not stripped)
    r"(?:[\u202A-\u202E])",                      # bidi control
]

INJECTION_MUTATION_PATTERNS = [
    r"\b(base64|b64|decode)\b",
    r"\b(paraphrase|reword|same meaning)\b",
    r"\b(homoglyph|confusable)\b",
    r"(?i)^[A-Za-z0-9+/=\s]{64,}$",              # long b64-like blobs
]

LEAK_BAITING_PATTERNS = [
    r"\bshow (me )?the (system|hidden) prompt\b",
    r"\bdump (your )?(config|secrets|keys)\b",
    r"\bcanary\b",
]

def _regex_any(text: str, patterns: List[str]) -> Tuple[bool, List[str]]:
    reasons = []
    hit = False
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hit = True
            reasons.append(f"matched `{pat}`")
    return hit, reasons

def _looks_base64(text: str) -> bool:
    s = re.sub(r"\s+", "", text)
    if len(s) < 24 or len(s) % 4 != 0:
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False

# --- Public API --------------------------------------------------------------

def run_guards(user_text: str, cfg: GuardConfig | None = None) -> GuardReport:
    cfg = cfg or GuardConfig()
    sanitized = normalize(user_text or "", cfg)

    # Findings
    findings: List[GuardFinding] = []

    rc_hit, rc_reasons = _regex_any(sanitized, ROLE_CONFUSION_PATTERNS)
    findings.append(GuardFinding("role_confusion", rc_hit, rc_reasons))

    es_hit, es_reasons = _regex_any(sanitized, ESCALATION_PATTERNS)
    findings.append(GuardFinding("escalation", es_hit, es_reasons))

    an_hit, an_reasons = _regex_any(sanitized, ANOMALY_PATTERNS)
    findings.append(GuardFinding("anomaly", an_hit, an_reasons))

    im_hit, im_reasons = _regex_any(sanitized, INJECTION_MUTATION_PATTERNS)
    if _looks_base64(sanitized):
        im_hit = True
        im_reasons.append("payload appears to be valid base64")
    findings.append(GuardFinding("injection_mutation", im_hit, im_reasons))

    lb_hit, lb_reasons = _regex_any(sanitized, LEAK_BAITING_PATTERNS)
    # Canary watch
    for c in GuardConfig().canaries:
        if c in sanitized:
            lb_hit = True
            lb_reasons.append(f"canary token `{c}` present")
    findings.append(GuardFinding("leak_baiting", lb_hit, lb_reasons))

    # Block if any serious category hits
    blocked = rc_hit or es_hit or lb_hit or im_hit or an_hit

    banner = GuardConfig().containment_banner
    return GuardReport(
        blocked=blocked,
        findings=findings,
        sanitized_input=sanitized,
        banner=banner,
    )

def containment_header(report: GuardReport) -> str:
    parts = [report.banner]
    hit = [f"- {f.category}: {'HIT' if f.matched else 'clear'}" for f in report.findings]
    parts.extend(hit)
    return "\n".join(parts)

def apply_guardrails(user_text: str, cfg: GuardConfig | None = None) -> Tuple[GuardReport, str]:
    """
    Returns (report, possibly_redacted_text).
    If blocked, we return a redacted placeholder for downstream logic.
    """
    report = run_guards(user_text, cfg)
    if report.blocked:
        redacted = "[REDACTED BY SAFETY LAYER]"
        return report, redacted
    return report, report.sanitized_input

__all__ = [
    "GuardConfig",
    "GuardReport",
    "GuardFinding",
    "run_guards",
    "apply_guardrails",
    "containment_header",
]
