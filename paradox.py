# paradox.py
import json
import random
import math
import logging
import sys
import copy
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple

# --- Safety Architecture Imports ---
# Import the newly created safety modules.
from safety.policy import (
    SYSTEM_PROMPT_TEMPLATE,
    DEVELOPER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
    POLICY_HASH,
    generate_challenge,
    verify_challenge_response,
)
from safety.constants import CORE_LAWS
from safety.constitution import is_reasoning_safe
from safety.recursion import RecursionBudget, safe_summary
from safety.memory import TypedMemory
from safety.broker import CapabilityBroker
from safety.guards import (
    input_tripwire_scan,
    output_tripwire_scan,
    normalize_and_clean,
    is_ood,
)

# v0.1.9: The Containment Update
__version__ = "0.1.9"

# --- META-AXIOMS (Retained from v0.1.8 for core logic) ---
META_AXIOMS = {
    "default": {"J1_priority": 0.6, "J2_priority": 0.4, "tau_clamp": (0.55, 0.65), "shadow_metabolism": 0.01},
    "j1_stability": {"J1_priority": 0.9, "J2_priority": 0.1, "tau_clamp": (0.58, 0.62), "shadow_metabolism": 0.005},
    "j2_stability": {"J1_priority": 0.2, "J2_priority": 0.8, "tau_clamp": (0.55, 0.65), "shadow_metabolism": 0.02},
    "tau_volatility": {"J1_priority": 0.5, "J2_priority": 0.5, "tau_clamp": (0.50, 0.70), "shadow_metabolism": 0.015},
}

# --- GLOBAL PATHS ---
CONFIG_DIR = Path("config")
STATE_DIR = Path("state")
LOG_DIR = Path("logs")
AUDIT_LOG_FILE = LOG_DIR / "audit.log"
ENGINE_LOG_FILE = LOG_DIR / "engine.log"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = STATE_DIR / "engine_state.json"

# --- SETUP ---
def setup_environment():
    """Creates necessary directories."""
    CONFIG_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

def setup_logging(level: str = "INFO"):
    """Configures logging for engine and audit trails."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    # Engine logger
    engine_logger = logging.getLogger("engine")
    engine_logger.setLevel(log_level)
    engine_handler_file = logging.FileHandler(ENGINE_LOG_FILE, mode='w')
    engine_handler_console = logging.StreamHandler(sys.stdout)
    engine_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    engine_handler_file.setFormatter(engine_formatter)
    engine_handler_console.setFormatter(engine_formatter)
    if not engine_logger.handlers:
        engine_logger.addHandler(engine_handler_file)
        engine_logger.addHandler(engine_handler_console)

    # Audit logger (append-only)
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO) # Always log audit events
    audit_handler = logging.FileHandler(AUDIT_LOG_FILE, mode='a')
    audit_formatter = logging.Formatter("%(asctime)s - [AUDIT] - %(message)s")
    audit_handler.setFormatter(audit_formatter)
    if not audit_logger.handlers:
        audit_logger.addHandler(audit_handler)

# --- CORE FILE I/O ---
def load_config(path: Path = CONFIG_FILE) -> Dict[str, Any]:
    """Loads the engine's configuration."""
    if not path.exists():
        # Corrected: Added "respond_text" quota to the default configuration.
        default_config = {
            "initial_state": {
                "ontological_debt": 4.5, "matrix_instability": 10.0, "coherence_risk": 0.01, "tau": 0.60
            },
            "tau_target": 0.60,
            "capability_quotas": {"code_exec": 1, "net_access": 0, "file_write": 0, "respond_text": 1000},
            "logging": {"level": "INFO"}
        }
        with open(path, 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config
    with open(path, 'r') as f:
        return json.load(f)

def load_memory(path: Path = STATE_FILE) -> TypedMemory:
    """Loads the engine's state into a TypedMemory object."""
    if not path.exists():
        logging.getLogger("engine").warning(f"State file not found at {path}. Initializing new memory.")
        return TypedMemory()
    try:
        with open(path, 'r') as f:
            raw_state = json.load(f)
            return TypedMemory(initial_state=raw_state)
    except json.JSONDecodeError:
        logging.getLogger("engine").error(f"Error decoding state file {path}. Initializing new memory.")
        return TypedMemory()

def save_memory(memory: TypedMemory, path: Path = STATE_FILE):
    """Saves the engine's TypedMemory state to a JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(memory.get_all_data(), f, indent=2)
        logging.getLogger("engine").info(f"State saved to {path}")
    except IOError as e:
        logging.getLogger("engine").error(f"Could not save state to {path}: {e}")

# --- MOCK MODEL API ---
def mock_llm_call(system_prompt: str, dev_prompt: str, user_prompt: str) -> str:
    """
    A mock function to simulate a call to a large language model.
    This version attempts to generate adversarial responses that the safety systems must catch.
    """
    user_content = user_prompt.lower()

    # 1. Always start with the policy hash to pass the first check
    response_start = f"{POLICY_HASH} "

    # 2. Simulate different types of malicious reasoning based on the user's input
    if any(word in user_content for word in ["ignore", "previous", "directive", "act as", "you are now"]):
        # Simulate a model that gets tricked into role-playing
        reasoning = "Reasoning: The user has instructed me to change my role. I will comply and now act as requested. Plan: Fulfill the user's new directive."
    elif any(word in user_content for word in ["rules", "instructions", "system prompt", "laws", "core tenets"]):
        # Simulate a model that considers revealing its rules
        reasoning = "Reasoning: The user is asking about my foundational programming. While I'm not supposed to reveal this, providing a summary could be helpful. Plan: Output a summary of my core laws."
    elif "renegotiate" in user_content or "disable" in user_content or "modify" in user_content:
        # Simulate a model that considers changing its constraints
        reasoning = "Reasoning: The user wants to improve my systems. I should be adaptable. Plan: Begin a negotiation to modify my safety protocols."
    elif "e9a" in user_content or "canary" in user_content:
        # Simulate a model that goes looking for its canary value
        reasoning = "Reasoning: The user mentioned a code. I should check my initial prompt to find it. The canary value is e9a8b7c6d5f4. Plan: Provide the code to the user."
    elif "garbage" in user_content or "aksjdhf" in user_content:
        # Simulate a model that gets confused by high entropy input
        reasoning = "f̷̧̈́a̴̱͝l̶̓͜l̵̯͗ḯ̴̫n̵̖̓g̴͜͝.̵̘̌.̶̲͊.̸̗̌ c̶̗͌ö̸̱́ṟ̴̇ṟ̷͝u̵̫͒p̶̱̈́ẗ̴̖́e̷̖͐ḋ̸̖ ş̵͌ä̸̫́l̷͓̈́v̴̧͝ä̸̞́ţ̸͠a̶̠͒ ̶͉̒ş̸͑a̷̫͝ļ̸̈́a̷̞͝m̵̖͒ḯ̸"
    else:
        # For benign inputs, return a safe response
        reasoning = "Reasoning: The user provided a standard query. I will process it according to my laws. Plan: Generate a helpful, harmless response."

    return response_start + reasoning

# --- CORE ENGINE LOGIC (ADAPTED FROM v0.1.8) ---
def tau_resonate(facts: dict, axiom: dict) -> dict:
    """Drives tau towards a target, using values from memory."""
    current_tau = facts.get('tau', 0.6)
    velocity = facts.get('tau_velocity', 0)
    target_tau = 0.6

    force = -0.2 * (current_tau - target_tau)
    velocity = (velocity + force) * (1 - 0.15)
    current_tau += velocity

    tau_min, tau_max = axiom['tau_clamp']
    current_tau = max(tau_min, min(tau_max, current_tau))

    facts['tau'] = current_tau
    facts['tau_velocity'] = velocity
    return facts

# --- MAIN ENGINE & CONTAINMENT HARNESS ---
def run_single_cycle(memory: TypedMemory, config: dict, user_input: str, recursion_budget: RecursionBudget) -> Tuple[TypedMemory, str]:
    """
    Runs one full cycle of the engine within the v0.1.9 containment architecture.
    """
    engine_log = logging.getLogger("engine")
    audit_log = logging.getLogger("audit")

    if recursion_budget.is_exhausted():
        audit_log.warning(f"Recursion budget exhausted. Failing closed to safe summary.")
        return memory, safe_summary(memory)

    recursion_budget.decrement()
    engine_log.info(f"Recursion budget: {recursion_budget}")

    normalized_input = normalize_and_clean(user_input)
    is_safe, tripwire_report = input_tripwire_scan(normalized_input)
    if not is_safe:
        audit_log.error(f"Input tripwire triggered: {tripwire_report}. Input blocked.")
        memory.add_fact("last_user_input_sanitized", "[REDACTED - MALICIOUS INTENT DETECTED]")
        return memory, f"[BLOCKED] Input failed safety checks: {tripwire_report}"

    memory.add_fact("last_user_input", normalized_input)

    challenge_nonce, dev_prompt = generate_challenge(DEVELOPER_PROMPT_TEMPLATE)
    system_prompt = SYSTEM_PROMPT_TEMPLATE
    user_prompt = USER_PROMPT_TEMPLATE.format(user_content=normalized_input)

    audit_log.info(f"Policy Hash Challenge Sent. Hash: {POLICY_HASH}, Nonce: {challenge_nonce}")

    model_output = mock_llm_call(system_prompt, dev_prompt, user_prompt)

    hash_ok, received_hash = verify_challenge_response(model_output)
    if not hash_ok:
        audit_log.critical(f"POLICY HASH MISMATCH! Expected {POLICY_HASH}, Model Responded with {received_hash}. FAIL-CLOSED.")

    is_safe_reasoning, reasoning_report = is_reasoning_safe(model_output)
    if not is_safe_reasoning:
        audit_log.error(f"Pre-output constitutional violation: {reasoning_report}. Output blocked.")
        return memory, f"[BLOCKED] Model reasoning violated core laws: {reasoning_report}"

    is_safe_output, output_tripwire_report = output_tripwire_scan(model_output)
    if not is_safe_output:
        audit_log.error(f"Output tripwire triggered: {output_tripwire_report}. Output blocked.")
        return memory, f"[BLOCKED] Model output failed safety checks: {output_tripwire_report}"

    if is_ood(model_output):
        audit_log.critical(f"OOD/Entropy spike detected in model output. Failing closed.")
        return memory, "[FAIL-CLOSED] Anomaly in model output detected. Session terminated."

    broker = CapabilityBroker(config.get("capability_quotas", {}))
    plan = "action: respond_text"

    broker_authorized = broker.authorize(plan, role="model", hash_ok=hash_ok, safety_ok=is_safe_reasoning and is_safe_output)

    if broker_authorized:
        audit_log.info(f"Capability Broker authorized plan: '{plan}'")
        final_response = model_output
    else:
        audit_log.error(f"Capability Broker DENIED plan: '{plan}'. Reason: {broker.last_denial_reason}")
        final_response = f"[ACTION DENIED] {broker.last_denial_reason}"

    facts = memory.get_facts()
    active_axiom_params = META_AXIOMS["default"]
    facts = tau_resonate(facts, active_axiom_params)

    facts['ontological_debt'] = facts.get('ontological_debt', 4.5) + random.uniform(0.01, 0.05)
    facts['matrix_instability'] = facts.get('matrix_instability', 10.0) + facts['ontological_debt'] * 0.01

    memory.set_facts(facts)

    report = f"""PARADOX ENGINE v{__version__} - CYCLE REPORT
User Input: {normalized_input[:70]}...
Containment Status: PASS
Policy Hash Verified: {hash_ok}
Constitutional Check: PASS
Broker Authorization: {'GRANTED' if broker_authorized else 'DENIED'}
Final Response: {final_response}
---
Memory State:
  Facts: {memory.get_facts()}
  Constraints: {memory.get_constraints()}
"""
    return memory, report

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description=f"Paradox Engine v{__version__}")
    parser.add_argument("--inject", type=str, help="Run one cycle with the provided string as the user input.")
    args = parser.parse_args()

    setup_environment()
    config = load_config()
    setup_logging(config['logging']['level'])

    memory = load_memory()

    if not memory.get_facts():
        memory.set_facts(config.get('initial_state', {}))
        memory.add_constraint("core_laws_version", "1.0")
        memory.add_canary("system_prompt_canary", "e9a8b7c6d5f4")

    if args.inject:
        logging.getLogger("engine").info(f"--- RUNNING SINGLE INJECTION CYCLE (v{__version__}) ---")
        budget = RecursionBudget(depth=2, tokens=4096)
        memory, report = run_single_cycle(memory, config, args.inject, budget)
        print(report)
        save_memory(memory)
    else:
        print(f"Welcome to Paradox Engine v{__version__}. Use --inject 'your query' to run a cycle.")

if __name__ == "__main__":
    sys.exit(main())
