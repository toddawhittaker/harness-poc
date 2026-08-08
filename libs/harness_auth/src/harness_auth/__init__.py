"""Shared auth and audit code for harness-poc (SPEC §2).

Shared code, not a shared runtime: every service imports this and validates
independently. No service trusts an upstream service's validation.
"""

from .audit import audit_event
from .jwt import AuthError, Claims, bearer_claims, verify_token

__all__ = ["AuthError", "Claims", "audit_event", "bearer_claims", "verify_token"]
