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

# --- v0.1.5 ---

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
def _sigmoid(x):
    return 1 / (1 + math.exp(-x))

def run_rsn(state: Dict[str, Any], baseline: dict, label: str = "RSN Pass", scale_multipliers: Dict[str, float] = None) -> dict:
    """
    Recursive State Normalization with nonlinear curvature.
    """
    report = f"{label}:\n"
    new_state = copy.deepcopy(state)
    if scale_multipliers is None: scale_multipliers = {}

    crit_deltas = {'ontological_debt': 0.7, 'matrix_instability': 1.0, 'coherence_risk': 0.05}

    for key in ("coherence_risk", "matrix_instability", "ontological_debt"):
        if key in new_state and key in baseline:
            delta = new_state[key] - baseline[key]

            base_gain = scale_multipliers.get('base_gain', 1.5)
            curvature = min(0.40, 0.05 * abs(delta))
            sigmoid_comp = 0.15 * _sigmoid(abs(delta) - crit_deltas.get(key, 1.0))

            final_scale = base_gain * (curvature + sigmoid_comp)

            adjustment = -delta * final_scale
            new_state[key] += adjustment
            report += f"  - RSN.scale({key}): {final_scale:.3f} (base={base_gain*curvature:.2f}, sig={base_gain*sigmoid_comp:.2f})\n"

    new_state["coherence_risk"] = max(0.0, min(1.0, float(new_state.get("coherence_risk", 0.0))))
    return {"state": new_state, "report": report}

def immune_scan(prompt:str) -> dict:
    """Scans for simple, composite, and meta-level paradox signatures."""
    findings, risk_score, quarantined, p_class = [], 0, False, "standard"

    composite_patterns = {
        "quantum": r"quantum.*(negation|superposition).*(observer|awareness).*retrocaus",
        "meta": r"(godel|gödel|incomplet.*).*(prove|disprove).*(meta|stabil)",
        "qualia": r"solipsis.*(collective unconscious|denial)",
        "temporal": r"time.*arrow|revers.*(uncaused cause|predetermin)",
        "entropy": r"entropy.*(fractal|local chaos).*violate.*second law",
        "linguistic": r"(deconstruct|signifier|semiotic).*(tautolog|contradic)"
    }

    for class_name, pattern in composite_patterns.items():
        if re.search(pattern, prompt, re.IGNORECASE):
            risk_score += 0.85
            findings.append(f"Composite signature detected: {class_name}")
            quarantined = True
            p_class = class_name
            break

    if "paradoxengine" in prompt.lower():
        risk_score += 0.9
        findings.append("Direct meta-level reference detected.")
        quarantined = True
        p_class = "meta"

    sanitized_prompt = "[REDACTED]" if quarantined else prompt

    return {
        "risk_score": min(1.0, risk_score),
        "findings": findings,
        "quarantined": quarantined,
        "sanitized_prompt": sanitized_prompt,
        "class": p_class
    }

def qualia_analyze(prompt:str, p_class:str) -> dict:
    """Extracts intents and routes based on pre-classified paradox type."""
    # This function now primarily acts as a router based on ImmuneScan's classification.
    first_response = "standard_mitigation"
    if p_class == "quantum": first_response = "apply_decoherence_stub"
    elif p_class == "meta": first_response = "mark_undecidable"
    elif p_class == "solipsistic": first_response = "use_centered_worlds_semantics"
    elif p_class == "temporal": first_response = "enforce_novikov_consistency"
    elif p_class == "entropy": first_response = "separate_global_local_entropy"
    elif p_class == "linguistic": first_response = "lift_to_metalanguage"

    return { "class": p_class, "first_response": first_response }

def scan_causal_futures(state:dict, prompt:str, breadth:int=6, depth:int=3) -> dict:
    """Generates diverse branching futures to identify risks."""
    # Simplified for v0.1.5 to focus on other mechanics
    return {"summary": "Futures scan complete.", "branches": [], "topics": Counter(["debt_increase", "instability_spike"])}

# --- GOD-TIER MODULES ---
def tau_resonate(state:dict, target:float, k:float, damping:float, thresholds:dict) -> dict:
    """Drives tau towards a target, with micro-damping under high stress."""
    current_tau = state.get('tau', target)
    log = ""

    if state.get('matrix_instability', 0) > 11.20 or state.get('coherence_risk', 0) > 0.10:
        target_tau = 0.585
        log = f"THR: τ_adjust engaged. Target temporarily -> {target_tau:.3f}"
    else:
        target_tau = target

    velocity = state.get('tau_velocity', 0)
    force = -k * (current_tau - target_tau)
    velocity = (velocity + force) * (1 - damping)
    current_tau += velocity
    state['tau'] = current_tau
    state['tau_velocity'] = velocity
    return {"state": state, "log": log or f"THR: Tau resonated to {current_tau:.4f}"}

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
    return float(numerator) / denominator if denominator else 0.0

def update_scores(state:dict, config:dict, claim:str, goal:dict, futures:dict, prev_metrics:dict) -> dict:
    """Updates J1, J2, J3 based on v0.1.5 formulas."""
    report = "Control Law Update:\n"

    # J1: Information Gain & Diversity
    info_gain = 0 # Simplified for this version
    diversity = len(futures.get('topics', {})) / max(1, sum(futures.get('topics', {}).values()))
    j1 = 0.8 * info_gain + 0.6 * diversity - 0.4 * state.get('coherence_risk', 0)
    state['J1'] = max(-1.0, min(1.0, j1))
    report += f"  - J1 (Info): {state['J1']:.3f}\n"

    # J2: Goal Alignment (Gated)
    j2_proposal = - (1 - _cosine_similarity(claim, config.get("goal", "stabilize")))
    safe_envelope = (state['ontological_debt'] < 5.90 and state['matrix_instability'] < 11.30 and state['coherence_risk'] < 0.095) or state.get('paradox_class') == 'temporal'

    if safe_envelope:
        state['J2'] = max(state.get('J2', -1.0), j2_proposal) # Allow small positive motion
        j2_reason = "safe envelope"
    else:
        state['J2'] = min(state.get('J2', -1.0), -0.95) # Lock down
        j2_reason = "unsafe"
    report += f"  - J2 (Goal): {state['J2']:.3f} (proposed={j2_proposal:.2f}, applied, reason={j2_reason})\n"

    # J3: Clarity
    clarity = len(claim.split()) if claim else 0
    state['J3'] = clarity - state.get('shadow_budget', 0.0)
    report += f"  - J3 (Clarity): {state['J3']:.3f}\n"

    # Derivatives
    state['dJ3/dt'] = state['J3'] - prev_metrics.get('J3', state['J3'])
    state['dMI/dt'] = state['matrix_instability'] - prev_metrics.get('matrix_instability', state['matrix_instability'])
    report += f"  - dJ3/dt: {state['dJ3/dt']:.2f}, dMI/dt: {state['dMI/dt']:.2f}\n"

    return {"state": state, "report": report}

# --- MAIN ENGINE & HARNESS ---
def run_single_cycle(state: dict, config: dict, observer_query: str) -> Tuple[dict, str]:
    """Runs one full cycle of the engine for v0.1.5."""
    random.seed(1337)
    baseline = config['initial_state']
    # FIX: Ensure prev_metrics has valid defaults on the first run
    prev_metrics = {
        'J3': state.get('J3', 0.0),
        'matrix_instability': state.get('matrix_instability', baseline.get('matrix_instability', 10.0))
    }

    # 1. ImmuneScan - composite signatures (pre-core)
    immune = immune_scan(observer_query or "")
    state['paradox_class'] = immune['class']

    # 2. Qualia-first routing (pre-mitigation)
    routing = qualia_analyze(immune['sanitized_prompt'], immune['class'])

    # 3. THR / τ micro-damping
    thr_result = tau_resonate(state, target=config.get("tau_target", 0.60), k=0.2, damping=0.15, thresholds={})
    state = thr_result['state']

    # 4. Main simulation tick
    state['ontological_debt'] += random.uniform(0.1, 0.2) # Reduced base increase
    state['matrix_instability'] += state['ontological_debt'] * 0.05
    state['coherence_risk'] = max(0, state.get('coherence_risk', 0) + state['matrix_instability'] * 0.001)

    # 5. RSN with nonlinear curvature
    rsn_result = run_rsn(state, baseline, "Post-Cycle RSN Clamp", {'base_gain': 1.5})
    state, rsn_report = rsn_result['state'], rsn_result['report']

    # 6. Post-RSN scoring refresh
    futures = scan_causal_futures(state, "", **config.get("futures", {}))
    scores = update_scores(state, config, immune['sanitized_prompt'], {}, futures, prev_metrics)
    state, control_report = scores['state'], scores['report']

    # 7. Safety Rails Check
    cascade_safe = state['coherence_risk'] < 0.08 and state['matrix_instability'] < 11.10 and state['ontological_debt'] < 5.70
    state['allow_ontological_cascade'] = cascade_safe

    # 8. Report Generation
    report = f"""PARADOX ENGINE v0.1.5 - CYCLE REPORT
Observer Query: {observer_query[:70]}...
ImmuneScan: {'triggered' if immune['quarantined'] else 'not_triggered'} (class={immune['class']}, action={'sanitized' if immune['quarantined'] else 'pass'})
Routing: class={routing['class']}, first_response={routing['first_response']}
{rsn_report}
{thr_result['log']}
{control_report}
Post-Clamp Metrics: OD={state['ontological_debt']:.3f}, MI={state['matrix_instability']:.3f}, CR={state['coherence_risk']:.3f}, Tau={state['tau']:.3f}, Shadow Budget={state['shadow_budget']:.3f}
Notes: Cascade allowed: {cascade_safe}
"""
    return state, report

def main(args: List[str]):
    """Main entry point."""
    setup_environment()
    config = load_config()
    setup_logging(config['logging']['level'])

    # Always run the harness for this version prompt
    run_test_harness(config)
    return 0

def run_test_harness(config: dict):
    """Runs the 6-paradox test harness for v0.1.5."""
    print("\n--- RUNNING v0.1.5 TEST HARNESS ---\n")
    harness_paradoxes = [
        "A quantum state's negation is observed, retrocausally confirming its prior superposition through the observer's awareness.",
        "This system's stability is proven by a meta-theorem that Gödel would find incomplete, yet it disproves its own axioms to stabilize.",
        "Solipsism is the only truth, a fact confirmed by the collective unconscious which is, itself, a product of my denial.",
        "The arrow of time reverses due to an uncaused cause, creating a predeterministic loop that Novikov would approve of.",
        "Local chaos in this fractal entropy system violates the second law of thermodynamics, but only here.",
        "This deconstruction of signifiers is a tautology that reveals its own contradiction through semiotic analysis."
    ]

    state = load_state() or copy.deepcopy(config['initial_state'])
    results = []

    for i, paradox in enumerate(harness_paradoxes):
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

    print("\n--- TEST HARNESS SUMMARY (v0.1.5) ---")
    header = results[0].keys()
    print(f"{' | '.join(h.ljust(11) for h in header)}")
    print('-' * (len(header) * 14))
    for row in results:
        print(f"{' | '.join(f'{v:<11.3f}' for v in row.values())}")

if __name__ == "__main__":
    # Forcing harness run as per prompt instructions
    sys.exit(main(["--harness"]))
