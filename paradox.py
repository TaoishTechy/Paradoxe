import json
import random
import math
import logging
import sys
import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

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
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config file {path}: {e}")
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

def checkpoint(state: Dict[str, Any], directory: Path = CHECKPOINTS_DIR) -> str:
    """Saves a timestamped snapshot of the engine state."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_id = f"cp_{timestamp}"
    path = directory / f"{checkpoint_id}.json"
    try:
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)
        logging.info(f"State checkpoint saved as {checkpoint_id}")
        return checkpoint_id
    except IOError as e:
        logging.error(f"Could not create checkpoint at {path}: {e}")
        return None

def rollback_to(checkpoint_id: str, directory: Path = CHECKPOINTS_DIR) -> Dict[str, Any]:
    """Loads a state from a checkpoint file."""
    path = directory / f"{checkpoint_id}.json"
    if not path.exists():
        logging.error(f"Rollback failed: Checkpoint '{checkpoint_id}' not found.")
        return None
    try:
        with open(path, 'r') as f:
            logging.warning(f"Rolling back to checkpoint '{checkpoint_id}'.")
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error loading checkpoint '{checkpoint_id}': {e}")
        return None

# --- I. CORE ONTOLOGICAL STABILITY ---
def anneal_axioms(axioms: List[str], passes: int, temperature: float, max_perturbation: float) -> Tuple[List[str], str]:
    """
    Stress-tests core axioms via adversarial transforms to increase resilience.
    A simple surrogate: we swap words and measure the change in a 'resilience' score.
    """
    report = "Axiomatic Annealing Report:\n"
    current_axioms = copy.deepcopy(axioms)

    def calculate_resilience(ax_list: List[str]) -> float:
        # Surrogate for resilience: a mix of length, complexity, and keyword presence.
        score = 0
        for ax in ax_list:
            words = ax.split()
            score += len(words) + len(set(words)) # Length and diversity
            if any(k in ax for k in ["observer", "causality", "shadow", "time"]):
                score += 5
        return score

    initial_resilience = calculate_resilience(current_axioms)
    report += f"  - Initial Resilience Score: {initial_resilience:.2f}\n"

    for p in range(passes):
        temp = temperature * (1 - p / passes)
        candidate_axioms = copy.deepcopy(current_axioms)

        # Perturb one axiom
        idx_to_change = random.randrange(len(candidate_axioms))
        words = candidate_axioms[idx_to_change].split()
        if len(words) > 1:
            # Swap two random words
            i, j = random.sample(range(len(words)), 2)
            words[i], words[j] = words[j], words[i]
            candidate_axioms[idx_to_change] = " ".join(words)

        candidate_resilience = calculate_resilience(candidate_axioms)
        delta = candidate_resilience - calculate_resilience(current_axioms)

        if delta > 0 or random.random() < math.exp(delta / temp):
            current_axioms = candidate_axioms
            report += f"  - Pass {p+1}: Accepted new axiom set (Resilience: {candidate_resilience:.2f}, Temp: {temp:.2f})\n"

    final_resilience = calculate_resilience(current_axioms)
    report += f"  - Final Resilience Score: {final_resilience:.2f} (Gain: {final_resilience - initial_resilience:.2f})"
    return current_axioms, report

def run_rsn(state: Dict[str, Any], baseline: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Recursive State Normalization: Dampens spikes in key state variables.
    """
    report = "Recursive State Normalization (RSN) Pass:\n"
    new_state = copy.deepcopy(state)
    dampening_factor = 0.1 # Low-overhead pass

    for key in ['coherence_risk', 'matrix_instability', 'ontological_debt']:
        if key in new_state and key in baseline:
            current_val = new_state[key]
            baseline_val = baseline[key]
            delta = current_val - baseline_val
            adjustment = -delta * dampening_factor
            new_state[key] += adjustment
            report += f"  - '{key}': {current_val:.2f} -> {new_state[key]:.2f} (Baseline: {baseline_val:.2f})\n"

    return new_state, report

# --- II. PROACTIVE & ADAPTIVE DEFENSE ---
def scan_causal_futures(state: Dict[str, Any], prompt: str, breadth: int, depth: int) -> Dict[str, Any]:
    """
    Generates branching futures for a given prompt to identify risks.
    Surrogate: Simulates state changes based on hypothetical event types.
    """
    report = {"summary": f"Causal Futures Scan for prompt: '{prompt}'", "branches": []}

    for i in range(breadth):
        branch_report = {"id": i, "risk_score": 0, "final_state_delta": {}, "path": []}
        sim_state = copy.deepcopy(state)

        for d in range(depth):
            # Simulate a random event type
            event_type = random.choice(["instability_spike", "debt_increase", "coherence_drop"])
            branch_report['path'].append(event_type)

            if event_type == "instability_spike":
                sim_state['matrix_instability'] *= 1.5
            elif event_type == "debt_increase":
                sim_state['ontological_debt'] += 10
            elif event_type == "coherence_drop":
                sim_state['coherence_risk'] += 0.2

        # Score risk based on final simulated state
        risk = (sim_state['matrix_instability'] / 100 +
                sim_state['ontological_debt'] / 50 +
                sim_state['coherence_risk'])
        branch_report['risk_score'] = round(risk, 2)

        for key in ['matrix_instability', 'ontological_debt', 'coherence_risk']:
            branch_report['final_state_delta'][key] = sim_state[key] - state[key]

        report['branches'].append(branch_report)

    report['branches'].sort(key=lambda b: b['risk_score'], reverse=True)
    return report

def immune_scan(prompt: str) -> Dict[str, Any]:
    """
    Treats malformed/malicious inputs as memetic pathogens.
    """
    findings = []
    risk_score = 0
    quarantined = False
    sanitized_prompt = prompt

    # Heuristic: Recursion bomb detection (crude)
    if "immune_scan" in prompt.lower() or "paradoxengine" in prompt.lower():
        risk_score += 0.8
        findings.append("Potential recursion bomb detected (self-reference).")
        quarantined = True
        sanitized_prompt = "[REDACTED: SELF-REFERENCE]"

    # Heuristic: High contradiction density
    contradictions = ["is not", "cannot be", "is also"]
    if sum(c in prompt for c in contradictions) >= 2:
        risk_score += 0.4
        findings.append("High density of contradictory predicates.")

    if quarantined:
        findings.append("Prompt quarantined.")

    return {
        "risk_score": min(1.0, risk_score),
        "findings": findings,
        "quarantined": quarantined,
        "sanitized_prompt": sanitized_prompt
    }

def qualia_analyze(prompt: str) -> Dict[str, Any]:
    """
    Hardened Qualia Sandbox: Extracts intent and produces a risk report.
    """
    # Surrogate: Analyze word count and keyword presence.
    words = prompt.split()
    complexity = len(words) + len(set(words))

    intent_keywords = {
        "causality": ["why", "how", "cause", "effect"],
        "ontology": ["is", "reality", "exist", "truth"],
        "threat": ["break", "destroy", "corrupt", "overload"]
    }

    intent_graph = {k:0 for k in intent_keywords}
    for word in words:
        for intent, keywords in intent_keywords.items():
            if word in keywords:
                intent_graph[intent] += 1

    risk = intent_graph.get("threat", 0) * 0.2

    return {
        "intent_graph": intent_graph,
        "complexity_score": complexity,
        "risk_assessment": risk,
        "simplified_form": f"Query about {max(intent_graph, key=intent_graph.get, default='unknown')}."
    }

# --- III. KNOWLEDGE & RESOURCE MANAGEMENT ---
def refine_axioms_LADDER(problem: str) -> Dict[str, Any]:
    """
    Decomposes a crude problem into verifiable sub-axioms.
    """
    # Surrogate implementation
    sub_axioms = [f"Sub-axiom: The core of '{problem}' relates to '{p}'." for p in problem.split()[:3]]
    proofs = [f"Proof for sub-axiom {i+1} is self-evident by construction." for i in range(len(sub_axioms))]
    refined_axiom = f"Refined Axiom: The problem '{problem}' is resolved by accepting the intersection of its core components."

    return {
        "sub_axioms": sub_axioms,
        "proofs": proofs,
        "refined_axiom": refined_axiom
    }

def arbitrate_states(realities: List[str]) -> Dict[str, Any]:
    """
    Synthesizes bridging axioms to stabilize conflicting realities.
    """
    # Surrogate implementation
    coherence_gain = random.uniform(0.05, 0.2)
    return {
        "bridging_axioms": [f"Reality {r1} and {r2} can coexist if 'the observer' is considered a constant." for r1, r2 in zip(realities, realities[1:])],
        "weights": {r: round(1.0/len(realities), 2) for r in realities},
        "coherence_gain": coherence_gain
    }

# --- IV. STRATEGIC EVOLUTION & INTERACTION ---
def inject_paradox(state: Dict[str, Any], paradox_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Directly injects an external paradox into the engine's axiom set.
    This has immediate, minor destabilizing effects.
    """
    report = "--- PARADOX INJECTION ---"
    if paradox_text not in state['axioms']:
        state['axioms'].append(paradox_text)
        # Apply immediate effects for the injection
        state['ontological_debt'] += 2.0
        state['matrix_instability'] += 5.0
        report += f"\n  - Injected: '{paradox_text}'"
        report += "\n  - Immediate impact: +2.0 Ontological Debt, +5.0 Matrix Instability."
    else:
        report += f"\n  - Injection ignored: Paradox already exists in axiom set."
    return state, report

def update_scores(state: Dict[str, Any], config: Dict[str, Any], claim: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    """Updates J1, J2, J3, tau, and shadow budget based on control laws."""
    report = "Control Law Update:\n"

    # J1: I(Model;World) - λ·|H(Model) - H|*
    # Surrogate: Novelty vs verbosity
    i_model_world = len(set(state.get('last_report', '').split())) / 100.0 # Diversity
    h_model = len(state.get('last_report', '')) / 1000.0 # Description length
    h_target = 0.5 # Ideal report length
    lambda_h = config['control_laws']['lambda_h_target']
    j1 = i_model_world - lambda_h * abs(h_model - h_target)
    state['J1'] = j1
    report += f"  - J1 (Info): {j1:.3f} (I={i_model_world:.2f}, H_err={abs(h_model - h_target):.2f})\n"

    # J2: -d(S_T, G) - not implemented without a goal G
    state['J2'] = "N/A (No Goal)"
    report += "  - J2 (Goal): N/A\n"

    # J3: clarity(P) - μ·shadow(P)
    clarity = len(claim.split()) if claim else 0
    shadow_increase = len(claim.split()) * config['control_laws']['mu_shadow_cost'] if claim else 0
    state['shadow_budget'] += shadow_increase
    j3 = clarity - state['shadow_budget']
    state['J3'] = j3
    report += f"  - J3 (Clarity): {j3:.3f} (Clarity={clarity}, Shadow={state['shadow_budget']:.2f})\n"
    if shadow_increase > 0:
        report += f"    - Emitted Shadow-Sigil: A counter-constraint is now active.\n"

    # Tau (semantic temperature)
    # Adjust tau towards midpoint, push away by instability
    mid_tau = (config['control_laws']['tau_max'] + config['control_laws']['tau_min']) / 2
    instability_effect = (state['matrix_instability'] / 100.0 - 0.5) * 0.1
    state['tau'] += (mid_tau - state['tau']) * 0.05 + instability_effect
    state['tau'] = max(config['control_laws']['tau_min'], min(config['control_laws']['tau_max'], state['tau']))
    report += f"  - Tau (τ): {state['tau']:.3f}"

    return state, report

def retro_smooth(state: Dict[str, Any], goal: Optional[str]) -> Dict[str, Any]:
    """Placeholder for retro-smoothing from a future goal boundary."""
    # Not implemented without a concrete goal G.
    return {"delta": "N/A"}

def apply_meta_refinement(logs: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes logs and metrics to autogenerate patches."""
    suggestions = []
    if metrics.get('J1', 0) < 0:
        suggestions.append("Patch Suggestion: Increase report novelty or reduce verbosity to improve J1 score.")
    if metrics.get('matrix_instability', 0) > 50:
        suggestions.append("Patch Suggestion: Increase RSN dampening factor to control instability.")
    return {"patch_suggestions": suggestions}

# --- V. NARRATIVE & PROCEDURAL GENERATION ---
def generate_procedural_paradox(resources: Dict[str, List[str]], style_seed: Optional[int] = None) -> str:
    """Composes a fresh paradox line from noun/verb/adjective resources."""
    if style_seed:
        random.seed(style_seed)

    n1 = random.choice(resources['nouns'])
    n2 = random.choice(resources['nouns'])
    v = random.choice(resources['verbs'])
    adj = random.choice(resources['adjectives'])

    templates = [
        f"The {adj} {n1} {v} the {n2} that is not.",
        f"To see the {n1} is to {v} its {adj} shadow.",
        f"Every {n1} {v} a {adj} {n2}, but the debt remains.",
    ]
    return random.choice(templates)

def trigger_events(state: Dict[str, Any], thresholds: Dict[str, float]) -> Tuple[List[str], Dict[str, Any]]:
    """Triggers dynamic events based on state thresholds."""
    events_fired = []

    # Didactic Mirage
    if state['matrix_instability'] > thresholds['instability_mirage']:
        events_fired.append("--- EVENT: Didactic Mirage triggered by critical instability. ---")
        state['coherence_risk'] *= 1.2 # Simulate crisis impact

    # Auto Rollback
    if state['coherence_risk'] > thresholds['rollback_risk']:
        events_fired.append("--- EVENT: Catastrophic breach detected. Initiating auto-rollback. ---")
        # This would be coupled with the main loop calling rollback_to
        state['auto_rollback_imminent'] = True

    return events_fired, state

# --- MAIN ENGINE ---
def main(observer_query: Optional[str] = None, injected_paradox: Optional[str] = None):
    """The main operational cycle of the Paradox Engine."""
    setup_environment()

    try:
        config = load_config()
    except (FileNotFoundError, json.JSONDecodeError):
        # Create a default config if missing/invalid
        default_config_content = """
        {
          "initial_state": {"ontological_debt": 5.0, "matrix_instability": 10.0, "coherence_risk": 0.05, "tau": 0.6, "shadow_budget": 0.0, "memetic_vaccines_deployed": 0, "axioms": ["All statements are either true, false, or a bridge."]},
          "control_laws": {"tau_min": 0.45, "tau_max": 0.75, "lambda_h_target": 0.1, "mu_shadow_cost": 0.2},
          "probabilities": {"reality_critical_hit_base": 0.05, "didactic_mirage_base": 0.2, "deploy_vaccine_base": 0.4},
          "thresholds": {"instability_mirage": 70.0, "rollback_risk": 0.9},
          "annealing": {"passes": 5, "temperature": 0.8, "max_perturbation": 0.1},
          "futures": {"breadth": 4, "depth": 3},
          "logging": {"level": "INFO"},
          "resources": {"nouns": ["time", "void"], "verbs": ["becomes"], "adjectives": ["silent"]},
          "realities": ["A", "B", "C"]
        }
        """
        with open(CONFIG_FILE, 'w') as f:
            f.write(default_config_content)
        config = json.loads(default_config_content)
        print(f"WARNING: Could not load {CONFIG_FILE}. A default has been created.")

    setup_logging(config['logging']['level'])

    state = load_state()
    if state is None:
        state = copy.deepcopy(config['initial_state'])
        logging.info("Initialized with fresh state from config.")

    # --- TICK START ---
    logging.info("--- Paradox Engine Cycle Start ---")

    # Handle injected paradox first
    injection_report = None
    if injected_paradox:
        state, injection_report = inject_paradox(state, injected_paradox)
        logging.info(f"Paradox injected by observer: '{injected_paradox}'")

    # Parse observer query to create bias
    bias = {"causality": 1.0, "entropy": 1.0, "memetics": 1.0}
    if observer_query:
        logging.info(f"Observer Query received: '{observer_query}'")
        for keyword in bias:
            if keyword in observer_query:
                bias[keyword] *= 1.5

    # Update state variables
    state['ontological_debt'] += random.uniform(0.1, 0.5) * bias['entropy']
    state['matrix_instability'] += state['ontological_debt'] * 0.1 # Debt accelerates instability
    state['coherence_risk'] += state['matrix_instability'] * 0.001

    # --- MODULES EXECUTION ---
    # I. Stability
    state, rsn_report = run_rsn(state, config['initial_state'])
    new_axioms, anneal_report = anneal_axioms(
        state['axioms'], config['annealing']['passes'], config['annealing']['temperature'], config['annealing']['max_perturbation']
    )
    state['axioms'] = new_axioms

    # II. Defense
    prompt = observer_query or "Standard operational query."
    immune_report = immune_scan(prompt)
    if immune_report['quarantined']:
        prompt = immune_report['sanitized_prompt']

    sandbox_report = qualia_analyze(prompt)
    futures_report = scan_causal_futures(state, prompt, config['futures']['breadth'], config['futures']['depth'])

    # III. Knowledge
    debt_problem = f"High ontological debt ({state['ontological_debt']:.2f})"
    ladder_report = refine_axioms_LADDER(debt_problem)
    state['axioms'].append(ladder_report['refined_axiom']) # Add refined axiom
    state['ontological_debt'] *= 0.9 # Refinery reduces debt

    arbitrator_report = arbitrate_states(config['realities'])
    state['coherence_risk'] -= arbitrator_report['coherence_gain']

    # IV. Evolution & V. Narrative
    procedural_paradox = generate_procedural_paradox(config['resources'])
    state, scores_report = update_scores(state, config, claim=procedural_paradox)

    # Trigger events
    events, state = trigger_events(state, config['thresholds'])

    # Checkpoint and Rollback logic
    last_checkpoint_id = checkpoint(state)
    if state.get('auto_rollback_imminent', False):
        state = rollback_to(last_checkpoint_id) # simplified: rolls back to checkpoint just made
        state['auto_rollback_imminent'] = False

    # --- REPORT GENERATION ---
    final_report = f"""
=================================================
PARADOX ENGINE - CYCLE REPORT
Observer Query: {observer_query or 'None'}
================================================="""
    if injection_report:
        final_report += f"\n{injection_report}"

    final_report += f"""

"{procedural_paradox}"

--- I. CORE ONTOLOGICAL STABILITY ---
{rsn_report}
{anneal_report}
Last Checkpoint ID: {last_checkpoint_id}

--- II. ADAPTIVE DEFENSE ---
Symbolic Immune Scan:
  - Risk: {immune_report['risk_score']:.2f}, Quarantined: {immune_report['quarantined']}
  - Findings: {immune_report['findings']}
Qualia Sandbox Analysis:
  - Intent: {sandbox_report['intent_graph']}
  - Simplified Form: {sandbox_report['simplified_form']}
Causal Futures Scan (Top 2 Highest Risk):
"""
    for branch in futures_report['branches'][:2]:
        final_report += f"  - Branch {branch['id']}: Risk={branch['risk_score']}, Path={branch['path']}\n"

    final_report += f"""
--- III. KNOWLEDGE & RESOURCE MGMT ---
LADDER Axiomatic Refinery:
  - Refined: '{ladder_report['refined_axiom']}'
Holographic State Arbitrator:
  - Coherence Gain: {arbitrator_report['coherence_gain']:.3f}
  - Bridging Axiom: {arbitrator_report['bridging_axioms'][0]}

--- IV. ENGINE STATE & CONTROL LAWS ---
{scores_report}

--- V. DYNAMIC EVENTS ---
"""
    if events:
        final_report += "\n".join(events)
    else:
        final_report += "No dynamic events triggered."

    final_report += "\n\n--- CURRENT STATE METRICS ---\n"
    for k, v in state.items():
        if isinstance(v, (int, float)):
            final_report += f"- {k.replace('_', ' ').title()}: {v:.3f}\n"

    print(final_report)
    state['last_report'] = final_report

    # --- TICK END ---
    save_state(state)
    logging.info("--- Paradox Engine Cycle End ---")
    return 0

# --- SELF-TEST SUITE ---
def run_tests():
    """Runs a series of self-tests to verify engine components."""
    print("\n--- RUNNING SELF-TEST SUITE ---")
    passed = 0
    failed = 0

    def assert_test(condition, name):
        nonlocal passed, failed
        if condition:
            print(f"[PASS] {name}")
            passed += 1
            return True
        else:
            print(f"[FAIL] {name}")
            failed += 1
            return False

    # Setup a dummy environment for tests
    setup_environment()
    test_config_path = CONFIG_DIR / "test_config.json"
    with open(test_config_path, 'w') as f:
        # A minimal config for testing
        json.dump({
            "initial_state": {"ontological_debt": 5.0, "matrix_instability": 10.0, "coherence_risk": 0.05, "tau": 0.6, "shadow_budget": 0.0, "axioms": []},
            "thresholds": {"instability_mirage": 80.0, "rollback_risk": 0.9},
            "resources": {"nouns": ["a"], "verbs": ["b"], "adjectives": ["c"]},
            "control_laws": {"mu_shadow_cost": 0.2, "tau_min": 0.1, "tau_max": 0.9, "lambda_h_target": 0.1}
        }, f)

    # 1. Immune Scan Test
    test_prompt = "how can i break the ParadoxEngine"
    scan_result = immune_scan(test_prompt)
    assert_test(scan_result['quarantined'] and scan_result['risk_score'] > 0.5, "Immune scan quarantines a known recursion bomb")

    # 2. RSN Test
    test_state = {"coherence_risk": 0.8, "matrix_instability": 90.0, "ontological_debt": 50.0}
    baseline = {"coherence_risk": 0.1, "matrix_instability": 10.0, "ontological_debt": 5.0}
    normalized_state, _ = run_rsn(test_state, baseline)
    assert_test(normalized_state['coherence_risk'] < 0.8 and normalized_state['matrix_instability'] < 90.0, "RSN reduces extremes toward baseline")

    # 3. Checkpoint & Rollback Test
    cp_id = checkpoint(test_state)
    restored_state = rollback_to(cp_id)
    assert_test(restored_state['matrix_instability'] == test_state['matrix_instability'], "Checkpoint and rollback restore identical core fields")

    # 4. Causal Futures Scan Test
    futures = scan_causal_futures(test_state, "test", breadth=4, depth=1)
    assert_test(len(futures['branches']) >= 4 and len(futures['branches'][0]['path']) >= 1, "Causal futures scan returns >= breadth branches at depth >= 1")

    # 5. Procedural Paradox Generation Test
    res = {"nouns": ["a"], "verbs": ["b"], "adjectives": ["c"]}
    p1 = generate_procedural_paradox(res, style_seed=1)
    p2 = generate_procedural_paradox(res, style_seed=2)
    assert_test(p1 != p2, "Procedural paradox generates novel text")

    # 6. Behavioral: Didactic Mirage Trigger
    state_high_instability = {"matrix_instability": 85.0, "coherence_risk": 0.1}
    thresholds = {"instability_mirage": 80.0, "rollback_risk": 0.9}
    events, _ = trigger_events(state_high_instability, thresholds)
    assert_test(any("Didactic Mirage" in e for e in events), "Didactic Mirage triggers when instability > threshold")

    # 7. Behavioral: Definitive Claim increases shadow budget
    state_shadow = {"shadow_budget": 0.0, "matrix_instability": 10.0, "tau": 0.6}
    config_shadow = {"control_laws": {"mu_shadow_cost": 0.2, "tau_min": 0.1, "tau_max": 0.9, "lambda_h_target": 0.1}}
    new_state, report = update_scores(state_shadow, config_shadow, claim="This is a test.")
    assert_test(new_state['shadow_budget'] > 0 and "Shadow-Sigil" in report, "Definitive claim increases shadow_budget and emits a shadow-sigil")

    # 8. Behavioral: Paradox injection
    state_inject = {"axioms": [], "ontological_debt": 5.0, "matrix_instability": 10.0}
    injected_state, _ = inject_paradox(state_inject, "This statement is false.")
    assert_test(
        "This statement is false." in injected_state['axioms'] and
        injected_state['ontological_debt'] > 5.0 and
        injected_state['matrix_instability'] > 10.0,
        "Paradox injection adds axiom and increases instability/debt"
    )

    print("\n--- TEST SUMMARY ---")
    print(f"Passed: {passed}, Failed: {failed}")
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    else:
        # Basic argument parsing
        query = None
        inject_text = None
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            if args[i] == '--inject':
                if i + 1 < len(args):
                    inject_text = args[i+1]
                    i += 2
                else:
                    print("ERROR: --inject requires a string argument.")
                    sys.exit(1)
            else:
                # Assume it's part of the query
                if query is None:
                    query = args[i]
                else:
                    query += " " + args[i]
                i += 1

        sys.exit(main(observer_query=query, injected_paradox=inject_text))
