"""
A2A (Agent-to-Agent) Adapter for Green MedAgentBench.

This module provides A2A protocol compliance for the MedAgentBench Green Agent,
wrapping the existing episode manager and evaluation logic.
"""

from .models import (
    AssessmentRequest,
    TaskUpdate,
    Artifact,
    A2AMessage,
)

# Lazy import to avoid requiring fastapi when not needed
def create_app():
    """Create FastAPI app (lazy import)."""
    from .a2a_green_server import create_app as _create_app
    return _create_app()

__all__ = [
    "AssessmentRequest",
    "TaskUpdate",
    "Artifact",
    "A2AMessage",
    "create_app",
]
