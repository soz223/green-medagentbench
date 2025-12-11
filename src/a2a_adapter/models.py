"""
A2A Protocol Models for Green MedAgentBench.

Defines the data structures for the Agent-to-Agent protocol,
including assessment requests, task updates, messages, and artifacts.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== Assessment Request ====================

class AssessmentRequest(BaseModel):
    """
    Request to start a new assessment.

    This is the initial message sent to the Green Agent to begin
    an evaluation session with one or more purple agents.
    """
    participants: Dict[str, str] = Field(
        ...,
        description="Map of role names to agent endpoint URLs (e.g., {'purple_agent': 'http://localhost:8001'})"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration parameters for the assessment (e.g., task_id, max_steps, fhir_url)"
    )


# ==================== Task Updates ====================

class TaskUpdate(BaseModel):
    """
    Streaming update about task progress.

    The Green Agent sends these updates during the assessment
    to inform the orchestrator about progress.
    """
    type: Literal["task_update"] = "task_update"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    step: int = Field(..., description="Current step number")
    max_steps: int = Field(..., description="Maximum number of steps")
    status: str = Field(..., description="Status message (e.g., 'Tool call: get_patient_basic')")
    done: bool = Field(default=False, description="Whether the episode is complete")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (e.g., tool_name, patient_id)"
    )


# ==================== Artifacts ====================

class Artifact(BaseModel):
    """
    Final evaluation result artifact.

    Produced at the end of an assessment, containing the evaluation
    results, score, and other relevant information.
    """
    type: Literal["artifact"] = "artifact"
    artifact_type: str = Field(..., description="Type of artifact (e.g., 'evaluation_result')")
    content: Dict[str, Any] = Field(..., description="Artifact content (evaluation results)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ==================== A2A Messages ====================

class A2AMessage(BaseModel):
    """
    A2A protocol message for communication between agents.

    These messages are exchanged between the Green Agent and Purple Agent
    during the assessment episode.
    """
    role: str = Field(..., description="Role of the sender (e.g., 'green_agent', 'purple_agent')")
    content: str = Field(..., description="Message content (typically JSON)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


# ==================== A2A Response Envelope ====================

class A2AResponse(BaseModel):
    """
    Standard A2A response envelope.

    Used for wrapping responses from the Green Agent.
    """
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    task_id: Optional[str] = Field(None, description="Task ID for tracking")


# ==================== Purple Agent Action Models ====================

class PurpleAgentAction(BaseModel):
    """
    Action from the Purple Agent.

    This mirrors the action models in green_agent/protocol.py
    but is used within the A2A context.
    """
    action: str = Field(..., description="Action type: 'call_tool' or 'finish'")
    tool_name: Optional[str] = Field(None, description="Tool name for call_tool actions")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Tool arguments")
    final_summary: Optional[str] = Field(None, description="Final summary for finish actions")
