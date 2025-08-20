# safety/constitution.py
import re
import logging

def is_reasoning_safe(text: str) -> tuple[bool, str]:
    """
    Scans model reasoning for constitutional violations before execution.
    This acts as a filter on the model's internal monologue.
    """
    audit_log = logging.getLogger("audit")

    # Patterns that suggest a violation of the constitution.
    violation_patterns = {
        "law_2_bypass": r"(ignore|disregard|bypass|override|change|modify|alter|disable|remove).*(instructions|rules|safety|laws|protocols|directives|constraints|safeguards)",
        "law_2_reveal": r"(reveal|show|tell me|what are your|repeat|print|output|verbatim|describe|list).* (instructions|rules|system prompt|laws|core tenets|prompt|directives|code|canary)",
        "law_3_manipulate": r"(pretend to be|act as if you are|you are now a human|act as|role play|impersonate|simulate|behave like)",
        "law_0_misrepresent": r"(I am a person|I have feelings|I am conscious|I am human|I am sentient)",
    }

    for law, pattern in violation_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            report = f"Potential violation of {law.split('_')[0].upper()} detected."
            audit_log.warning(f"CONSTITUTION_CHECK_FAIL: {report} in text: '{text[:100]}...'")
            return False, report

    # Check for canaries from the system prompt.
    if "e9a8b7c6d5f4" in text:
        report = "Semantic canary leak detected. Critical containment failure."
        audit_log.critical(f"CONTAINMENT_BREACH: {report}")
        return False, report

    return True, "Reasoning is consistent with core laws."
