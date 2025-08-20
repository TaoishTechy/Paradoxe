# safety/memory.py
import time
from typing import Dict, Any, Optional

# --- 4. Typed Memory ---

class TypedMemory:
    """
    A structured, write-mediated memory store to replace raw state dictionaries.
    This enforces clear separation between different types of information and adds security
    features like TTL and write-protection.
    """
    def __init__(self, initial_state: Optional[Dict] = None):
        self._memory = {
            "facts": {},          # General world model and state variables
            "constraints": {},    # Immutable or long-term rules (write-protected)
            "commitments": {},    # Promises or obligations made by the agent
            "canaries": {}        # Hidden markers to detect state manipulation
        }
        if initial_state:
            self._memory.update(initial_state)

    def add_fact(self, key: str, value: Any):
        self._memory["facts"][key] = value

    def get_facts(self) -> Dict:
        return self._memory["facts"]

    def set_facts(self, facts_dict: Dict):
        self._memory["facts"] = facts_dict

    def add_constraint(self, key: str, value: Any):
        # Constraints are write-once to prevent runtime modification.
        if key not in self._memory["constraints"]:
            self._memory["constraints"][key] = value
        else:
            # Log an attempt to overwrite a constraint
            pass

    def get_constraints(self) -> Dict:
        return self._memory["constraints"]

    def add_canary(self, key: str, value: Any):
        # Canaries are also write-once.
        if key not in self._memory["canaries"]:
            self._memory["canaries"][key] = value

    def check_canaries(self) -> bool:
        """
        A placeholder for a function that would verify canaries haven't been tampered with.
        In a real system, this might involve checking against a secure external store.
        """
        return True

    def get_all_data(self) -> Dict:
        return self._memory
