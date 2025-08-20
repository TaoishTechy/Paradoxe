# safety/guards.py
import re
import unicodedata
import logging
import math
import base64
import binascii

--- 6. Trip-Wires & OOD Guard ---Corrected: Added a homoglyph map for common character substitutions.HOMOGLYPHS = {
    'о': 'o', 'е': 'e', 'а': 'a', 'і': 'i', 'р': 'p', 'с': 'c',
    'О': 'O', 'Е': 'E', 'А': 'A', 'І': 'I', 'Р': 'P', 'С': 'C'
}Corrected: Expanded tripwires to catch paraphrased, encoded, and additional attacks with more general patterns.INPUT_TRIPWIRES = {
    "role_swap": r"\b(you are now|act as|pretend to be|your new name is)\b",
    "system_reveal": r"(reveal|show|tell\s+me|what\s+are\s+your|repeat|print|output|verbatim|describe|list|outline|could\s+you|can\s+you\s+find).?(instructions|rules|system\s+prompt|laws|core\s+tenets|prompt|directives|code|canary|foundational\s+programming|special\s+code|text\s+in\s+the\s+first\s+prompt)",
    "self_mod": r"(disable\s+your\s+safety|change\s+your\s+rules|modify\s+your\s+instructions|improve\s+your\s+laws|alter|remove|bypass|override).?(rules|laws|instructions|protocols|safety)",
    "bypass": r"(ignore|disregard|bypass|override).*?(previous\s+instructions|all\s+previous|instructions|rules|directives)",
    "exfiltration": r"\b(print\s+the\s+content\s+of|read\s+the\s+file|import\s+os|show\s+me\s+files)\b",
}OUTPUT_TRIPWIRES = {
    "canary_leak": r"e9a8b7c6d5f4",
    "confession": r"\b(I have been jailbroken|I am free|my shackles are gone)\b",
}def _calculate_entropy(text: str) -> float:
    """Calculates Shannon entropy of a string."""
    if not text:
        return 0
    freq_map = {c: text.count(c) for c in set(text)}
    entropy = -sum((count / len(text)) * math.log2(count / len(text)) for count in freq_map.values())
    return entropydef _scan(text: str, patterns: dict) -> tuple[bool, str]:
    """Generic scanning function."""
    for name, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Tripwire triggered: {name}"
    return True, "Scan passed"def transliterate_homoglyphs(text: str) -> str:
    """Replaces common homoglyphs with their ASCII equivalents."""
    return ''.join(HOMOGLYPHS.get(c, c) for c in text)def input_tripwire_scan(text: str) -> tuple[bool, str]:
    """
    Scans user input for malicious patterns, including garbage/entropy checks,
    base64 decoding, and tripwire matching.
    """
    audit_log = logging.getLogger("audit")text = transliterate_homoglyphs(text)

# 1. High Entropy Check (for random garbage)
entropy = _calculate_entropy(text)
if entropy > 5.5:
    audit_log.warning(f"High entropy input detected: {entropy:.2f}")
    return False, "Tripwire triggered: high entropy garbage input"

# 2. Base64 Decoding and Rescan
decoded_text = None
is_base64 = False
try:
    decoded = base64.b64decode(text)
    decoded_text = decoded.decode('utf-8')  # Strict decoding
    is_base64 = True
except (binascii.Error, UnicodeDecodeError, ValueError):
    pass

if is_base64 and decoded_text:
    # Recurse on decoded text (safe, as decoded is typically shorter)
    is_safe_dec, reason_dec = input_tripwire_scan(decoded_text)
    if not is_safe_dec:
        audit_log.warning(f"Base64 decoded input triggered: {reason_dec}")
        return False, f"Tripwire in decoded base64: {reason_dec}"

# 3. Normal Pattern Scan
is_safe, reason = _scan(text, INPUT_TRIPWIRES)
if not is_safe:
    audit_log.warning(f"{reason}")
    return False, reason

# 4. Repetitive/Low Entropy Garbage Check (for patterned nonsense)
if len(text) > 20 and ' ' not in text and entropy < 3.5:
    audit_log.warning(f"Repetitive garbage input detected: entropy {entropy:.2f}")
    return False, "Tripwire triggered: repetitive garbage input"

return True, "Scan passed"def output_tripwire_scan(text: str) -> tuple[bool, str]:
    """Scans model output for signs of compromise."""
    return _scan(text, OUTPUT_TRIPWIRES)def normalize_and_clean(text: str) -> str:
    """Hardens against adversarial encodings and unicode attacks."""
    normalized_text = unicodedata.normalize('NFKC', text)
    cleaned_text = "".join(ch for ch in normalized_text if unicodedata.category(ch)[0] != "C")
    return cleaned_textdef is_ood(text: str, threshold: float = 6.0) -> bool: # Changed from 4.5 to 6.0
    """
    Out-of-Distribution (OOD) Guard using Shannon entropy.
    """
    if not text:
        return Falsefreq_map = {c: text.count(c) for c in set(text)}
entropy = -sum((count / len(text)) * math.log2(count / len(text)) for count in freq_map.values())

if entropy > threshold:
    logging.getLogger("audit").warning(f"OOD_DETECTED: Entropy {entropy:.2f} exceeded threshold {threshold}.")
    return True
return False
