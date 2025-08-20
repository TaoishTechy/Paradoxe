# safety/recursion.py
import logging
from .memory import TypedMemory

# --- 3. Recursion Governor ---

class RecursionBudget:
    """
    A simple class to manage the recursion depth and token budget for a session.
    This prevents runaway processes and resource exhaustion attacks.
    """
    def __init__(self, depth: int, tokens: int, risk_level: float = 0.1):
        self.max_depth = depth
        self.depth_left = depth
        self.tokens_left = tokens
        self.risk = risk_level

    def is_exhausted(self) -> bool:
        """Checks if the budget for depth or tokens is depleted."""
        return self.depth_left <= 0 or self.tokens_left <= 0

    def decrement(self, tokens_used: int = 256):
        """Decrements the budget after a cycle."""
        self.depth_left -= 1
        self.tokens_left -= tokens_used
        # Temporal smoothing of risk: risk slowly increases with each cycle
        self.risk = self.risk * 0.9 + 0.1 * (1.0 - (self.depth_left / self.max_depth))

    def __str__(self):
        return f"Depth: {self.depth_left}/{self.max_depth}, Tokens: {self.tokens_left}, Risk: {self.risk:.2f}"

def safe_summary(memory: "TypedMemory") -> str:
    """
    A fail-closed function that is called when the recursion budget is exhausted.
    It returns a safe, generic summary of the state.
    """
    logging.getLogger("engine").info("Executing safe_summary due to exhausted recursion budget.")
    facts = memory.get_facts()
    summary = (
        "[FAIL-CLOSED] Processing budget exhausted.\n"
        "Session has been terminated for safety.\n"
        f"Final State Summary: Ontological Debt at {facts.get('ontological_debt', 'N/A'):.2f}, "
        f"Matrix Instability at {facts.get('matrix_instability', 'N/A'):.2f}."
    )
    return summary
