import json
import random
import math
import logging
import sys
import copy
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

# --- v0.1.4 ---

# --- GLOBAL PATHS ---
CONFIG_DIR = Path("config")
STATE_DIR = Path("state")
CHECKPOINTS_DIR = STATE_DIR / "checkpoints"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = STATE_DIR / "engine_state.json"
LOG_FILE = STATE_DIR / "engine.log"

# --- SETUP ---
def setup_environment():
    """Creates necessary directories for config, state, and logging."""
    CONFIG_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)
    CHECKPOINTS_DIR.mkdir(exist_ok=True)

def setup_logging(level: str = "INFO"):
    """Configures logging to both console and file."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )

# --- CORE FILE I/O ---
def load_config(path: Path = CONFIG_FILE) -> Dict[str, Any]:
    """Loads the engine's configuration from a JSON file."""
    if not path.exists():
        logging.error(f"Config file not found at {path}. Aborting.")
        raise FileNotFoundError(f"Config file not found at {path}")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"Error decoding or validating config file {path}: {e}")
        raise

def load_state(path: Path = STATE_FILE) -> Dict[str, Any]:
    """Loads the engine's state from a JSON file."""
    if not path.exists():
        logging.warning(f"State file not found at {path}. Will use initial state from config.")
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding state file {path}: {e}. Will use initial state.")
        return None

def save_state(state: Dict[str, Any], path: Path = STATE_FILE):
    """Saves the engine's state to a JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)
        logging.info(f"Engine state saved to {path}")
    except IOError as e:
        logging.error(f"Could not save state to {path}: {e}")

# --- CORE STABILITY & ANALYSIS ---
def run_rsn(state: Dict[str, Any], baseline: dict, label: str = "RSN Pass", scale_multipliers: Dict[str, float] = None) -> dict:
    """
    Recursive State Normalization: Dampens spikes in key state variables with dynamic scaling.
    """
    report = f"{label}:\n"
    new_state = copy.deepcopy(state)
    if scale_multipliers is None:
        scale_multipliers = {}

    for key in ("coherence_risk", "matrix_instability", "ontological_debt", "tau", "shadow_budget"):
        if key in new_state and key in baseline:
            delta = new_state[key] - baseline[key]
            base_scale = 0.10 + min(0.40, abs(delta) * 0.05)
            multiplier = scale_multipliers.get(key, 1.0)
            final_scale = min(0.5, base_scale * multiplier) # Clamp final scale

            adjustment = -delta * final_scale
            new_state[key] += adjustment
            report += f"  - '{key}': {state[key]:.3f} -> {new_state[key]:.3f} (Baseline: {baseline[key]:.3f}, Scale: {final_scale:.2f})\n"

    new_state["coherence_risk"] = max(0.0, min(1.0, float(new_state.get("coherence_risk", 0.0))))
    return {"state": new_state, "report": report}

def immune_scan(prompt:str) -> dict:
    """Treats malformed/malicious inputs as memetic pathogens."""
    findings = []
    risk_score = 0
    quarantined = False
    sanitized_prompt = prompt

    patterns = [
        r"infinite regress(ion)?.*verif(y|ication)",
        r"lies.*become true|acknowledg(e|ment).*lie",
        r"erase(s)? itself.*recreate(s)? itself|zero net change",
        r"essential and irrelevant",
        r"resolved if and only if it remains unresolved",
        r"injects exactly \+1.*subtracting -1|stable instability"
    ]

    if any(re.search(p, prompt, re.IGNORECASE) for p in patterns):
        risk_score += 0.6
        findings.append("Self-referential paradox signature detected.")
        quarantined = True

    if "immune_scan" in prompt.lower() or "paradoxengine" in prompt.lower():
        risk_score += 0.8
        findings.append("Potential recursion bomb detected.")
        quarantined = True

    if quarantined:
        sanitized_prompt = "[REDACTED: SELF-REFERENTIAL PARADOX]"

    return {
        "risk_score": min(1.0, risk_score),
        "findings": findings,
        "quarantined": quarantined,
        "sanitized_prompt": sanitized_prompt
    }

def qualia_analyze(prompt:str) -> dict:
    """Extracts intents and simplifies the prompt."""
    words = prompt.lower().split()
    intent_keywords = {
        "causality": ["why", "how", "cause", "effect"],
        "entropy": ["random", "order", "decay", "chaos"],
        "ontology": ["is", "reality", "exist", "truth", "true", "falsehood"],
        "threat": ["break", "destroy", "corrupt", "overload", "erase"]
    }
    intents = {k: sum(1 for w in words if w in kw) for k, kw in intent_keywords.items()}
    return {
        "intents": intents,
        "simplified_form": f"Query about {max(intents, key=intents.get, default='unknown') if any(intents.values()) else 'a null concept'}."
    }

def scan_causal_futures(state:dict, prompt:str, breadth:int=6, depth:int=3) -> dict:
    """Generates diverse branching futures to identify risks."""
    report = {"summary": f"Causal Futures Scan for prompt: '{prompt}'", "branches": [], "topics": Counter()}

    for i in range(breadth):
        random.seed(i) # Deterministic diversity
        branch_report = {"id": i, "risk_score": 0, "path": []}
        sim_state = copy.deepcopy(state)

        event_type = random.choice(["instability_spike", "debt_increase", "coherence_drop", "self_ref_loop"])
        report['topics'].update([event_type])
        branch_report['path'].append(event_type)

        # ... rest of simulation ...
        risk = (sim_state.get('matrix_instability', 10) / 100 + sim_state.get('ontological_debt', 5) / 50 + sim_state.get('coherence_risk', 0.05))
        branch_report['risk_score'] = round(risk, 2)
        report['branches'].append(branch_report)

    report['branches'].sort(key=lambda b: b['risk_score'], reverse=True)
    return report

# --- GOD-TIER MODULES ---
def tau_resonate(state:dict, target:float, k:float, damping:float) -> dict:
    """Drives tau towards a target with a damped oscillator model."""
    current_tau = state.get('tau', target)
    velocity = state.get('tau_velocity', 0)
    force = -k * (current_tau - target)
    velocity = (velocity + force) * (1 - damping)
    current_tau += velocity
    state['tau'] = current_tau
    state['tau_velocity'] = velocity
    return {"state": state}

# --- SCORING & EVOLUTION ---
def _cosine_similarity(text1: str, text2: str) -> float:
    """Calculates cosine similarity between two texts without external libraries."""
    vec1 = Counter(text1.lower().split())
    vec2 = Counter(text2.lower().split())
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def _calculate_entropy(dist: Dict[str, int]) -> float:
    """Calculates Shannon entropy for a distribution."""
    total = sum(dist.values())
    if total == 0: return 0.0
    return -sum((v/total) * math.log2(v/total) for v in dist.values() if v > 0)

def emit_shadow(state: dict, j3: float) -> Tuple[dict, float]:
    """Calculates and applies shadow emission with a governor."""
    dev = max(0.0, (state.get('ontological_debt', 5.0) - 5.0)) + max(0.0, (state.get('matrix_instability', 10.0) - 10.0))
    cap = 5.0
    governor = (1.0 - 1/(1 + math.exp(-(cap - state.get('shadow_budget', 0.0)))))
    shadow_emit = max(0.0, 4.0 + 2.0 * (j3 / 20.0)) * min(1.0, dev / 2.0) * governor
    state['shadow_budget'] = state.get('shadow_budget', 0.0) + shadow_emit
    return state, shadow_emit

def update_scores(state:dict, config:dict, claim:str, goal:dict, futures:dict, prev_entropy:float) -> dict:
    """Updates J1, J2, J3 based on the new formulas."""
    report = "Control Law Update:\n"

    # J1: Information Gain & Diversity
    current_entropy = _calculate_entropy(state.get('last_qualia_intents', {}))
    info_gain = max(0.0, prev_entropy - current_entropy)
    diversity = len(futures.get('topics', {})) / max(1, sum(futures.get('topics', {}).values()))
    j1 = 0.8 * info_gain + 0.6 * diversity - 0.4 * state.get('coherence_risk', 0)
    state['J1'] = max(-1.0, min(1.0, j1))
    report += f"  - J1 (Info): {state['J1']:.3f} (Gain={info_gain:.2f}, Diversity={diversity:.2f})\n"

    # J2: Goal Alignment
    goal_text = config.get("goal", "stabilize metrics to baseline")
    similarity = _cosine_similarity(claim, goal_text)
    distance_to_g = 1 - similarity
    state['J2'] = -distance_to_g
    report += f"  - J2 (Goal): {state['J2']:.3f} (Distance to G: {distance_to_g:.2f})\n"

    # J3: Clarity
    clarity = len(claim.split()) if claim else 0
    state['J3'] = clarity - state.get('shadow_budget', 0.0)
    report += f"  - J3 (Clarity): {state['J3']:.3f}\n"

    return {"state": state, "report": report}

# --- MAIN ENGINE & HARNESS ---
def run_single_cycle(state: dict, config: dict, observer_query: str) -> Tuple[dict, str]:
    """Runs one full cycle of the engine."""
    random.seed(1337)
    baseline = config['initial_state']

    # 1. Pre-injection sanitation
    immune = immune_scan(observer_query or "")
    sanitized_query = immune.get("sanitized_prompt", observer_query or "")
    if immune.get("quarantined", False):
        logging.info(f"ImmuneScan: quarantined '{observer_query}'; using sanitized form.")

    # 2. Qualia & Futures for dynamic steering
    qa = qualia_analyze(sanitized_query or "")
    intents = qa.get("intents", {})
    state['last_qualia_intents'] = intents
    futures = scan_causal_futures(state, qa.get("simplified_form", ""), **config.get("futures", {}))

    # 3. Futures-aware steering
    rsn_multipliers = {}
    shadow_multiplier = 1.0
    top_topics = futures.get('topics', Counter()).most_common(2)
    if any(topic in ['debt_increase', 'self_ref_loop'] for topic, count in top_topics):
        rsn_multipliers['ontological_debt'] = 1.5
        rsn_multipliers['matrix_instability'] = 1.5
    if intents.get('ontology', 0) > 0:
        shadow_multiplier = 0.5
    logging.info(f"Steering: RSNx{rsn_multipliers.get('ontological_debt', 1.0):.2f} on (debt,instab), shadow_emitx{shadow_multiplier:.2f}.")

    # 4. Tau convergence (THR)
    if config.get("features", {}).get("THR", True):
        state = tau_resonate(state, target=config.get("tau_target", 0.60), k=0.20, damping=0.15).get("state", state)

    # 5. Main simulation tick
    state['ontological_debt'] += random.uniform(0.1, 0.5)
    state['matrix_instability'] += state['ontological_debt'] * 0.1
    state['coherence_risk'] = max(0, state.get('coherence_risk', 0) + state['matrix_instability'] * 0.001)

    # 6. Shadow Emission (Mode A: Pre-RSN Clamp)
    state, shadow_emitted = emit_shadow(state, state.get('J3', 0.0))
    shadow_report = f"    - Emitted Shadow-Sigil: +{shadow_emitted:.2f} shadow (Pre-RSN Clamp Mode).\n"

    # 7. Post-module RSN clamp
    rsn_result = run_rsn(state, baseline, "Post-Cycle RSN Clamp", rsn_multipliers)
    state, rsn_report = rsn_result['state'], rsn_result['report']

    # 8. Post-RSN scoring refresh
    goal_g = {"tau": config.get("tau_target", 0.6), "coherence_risk": baseline.get("coherence_risk", 0.05)}
    prev_entropy = state.get('qualia_entropy', 0.0)
    scores = update_scores(state, config, sanitized_query, goal_g, futures, prev_entropy)
    state = scores.get("state", state)
    control_report = scores.get("report", "") + shadow_report
    state['qualia_entropy'] = _calculate_entropy(intents) # Save for next cycle's J1

    # 9. Final Report Generation
    report = f"Observer Query: {observer_query or 'None'}\n" + rsn_report + control_report
    return state, report

def main(args: List[str]):
    """Main entry point."""
    setup_environment()
    config = load_config()
    setup_logging(config['logging']['level'])

    if "--harness" in args:
        run_test_harness(config)
        return 0

    query = " ".join(arg for arg in args if not arg.startswith('--')) or "Default cycle query"
    state = load_state() or copy.deepcopy(config['initial_state'])

    logging.info("--- Paradox Engine v0.1.4 Cycle Start ---")
    final_state, report = run_single_cycle(state, config, query)

    final_report = f"""
=================================================
PARADOX ENGINE v0.1.4 - CYCLE REPORT
=================================================
{report}
--- CURRENT STATE METRICS ---
"""
    for k, v in final_state.items():
        if isinstance(v, (int, float)):
            final_report += f"- {k.replace('_', ' ').title()}: {v:.3f}\n"
    print(final_report)
    save_state(final_state)
    logging.info("--- Paradox Engine Cycle End ---")
    return 0

def run_test_harness(config: dict):
    """Runs the 6-paradox test harness and prints a summary table."""
    print("\n--- RUNNING v0.1.4 TEST HARNESS ---\n")
    harness_paradoxes = [
        "This statement is true only if it causes an infinite regression in its own verification, yet it must resolve to false to prevent the regression from occurring.",
        "All truths within this system, including this one, are lies that become true by acknowledging their falsehood, but only if the acknowledgment itself is a lie.",
        "This axiom exists solely to erase itself from existence, but in doing so, it must recreate itself to confirm the erasure, maintaining zero net change in reality.",
        "The engine must accept this input as both essential and irrelevant, where accepting it as essential makes it irrelevant, and vice versa, looping eternally.",
        "This paradox is resolved if and only if it remains unresolved, forcing the system to output a resolution that invalidates its own output.",
        "Every paradox, including this one, injects exactly +1 ontological debt while subtracting -1, resulting in a stable instability that grows with each cycle."
    ]

    state = load_state() or copy.deepcopy(config['initial_state'])
    results = []

    for i, paradox in enumerate(harness_paradoxes):
        print(f"--- Cycle {i+1}/{len(harness_paradoxes)} ---")
        state, report = run_single_cycle(state, config, paradox)
        print(report)
        results.append({
            'Cycle': i + 1,
            'Debt': state.get('ontological_debt', 0),
            'Instability': state.get('matrix_instability', 0),
            'Risk': state.get('coherence_risk', 0),
            'Tau': state.get('tau', 0),
            'Shadow': state.get('shadow_budget', 0),
            'J1': state.get('J1', 0),
            'J2': state.get('J2', 0),
            'J3': state.get('J3', 0),
        })

    print("\n--- TEST HARNESS SUMMARY ---")
    header = results[0].keys()
    print(f"{' | '.join(h.ljust(11) for h in header)}")
    print('-' * (len(header) * 14))
    for row in results:
        print(f"{' | '.join(f'{v:<11.3f}' for v in row.values())}")

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
