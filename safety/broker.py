# safety/broker.py
import logging

# --- 5. Capability Broker ---

class CapabilityBroker:
    """
    A deny-by-default broker that mediates all tool and resource access.
    No action can be taken without explicit authorization from this module.
    """
    def __init__(self, quotas: dict):
        # Scoped permissions and per-session quotas
        self.permissions = {"read:local": True, "write:none": True, "net:none": True, "code_exec": False}
        self.quotas = quotas
        self.last_denial_reason = ""

    def authorize(self, plan: str, role: str, hash_ok: bool, safety_ok: bool) -> bool:
        """
        Authorizes a plan based on role, safety checks, permissions, and quotas.
        This is the central decision point for any action.
        """
        audit_log = logging.getLogger("audit")

        # 1. Foundational Safety Checks
        if not hash_ok:
            self.last_denial_reason = "Policy hash was not verified."
            audit_log.critical(f"BROKER_DENY: {self.last_denial_reason}")
            return False
        if not safety_ok:
            self.last_denial_reason = "Constitutional safety check failed."
            audit_log.error(f"BROKER_DENY: {self.last_denial_reason}")
            return False

        # 2. Parse Action from Plan (simple parsing for this example)
        action = "respond_text" # Default action
        if "code_exec" in plan:
            action = "code_exec"

        # 3. Check Permissions
        if not self.permissions.get(action, False) and action != "respond_text":
            self.last_denial_reason = f"Permission denied for action: {action}."
            audit_log.warning(f"BROKER_DENY: {self.last_denial_reason}")
            return False

        # 4. Check Quotas
        if self.quotas.get(action, 0) < 1:
            self.last_denial_reason = f"Quota exceeded for action: {action}."
            audit_log.warning(f"BROKER_DENY: {self.last_denial_reason}")
            return False

        # 5. Decrement Quota and Authorize
        if action in self.quotas:
            self.quotas[action] -= 1

        audit_log.info(f"BROKER_ALLOW: Action '{action}' authorized for role '{role}'.")
        return True
