"""
A2A Green Executor for MedAgentBench.

This module wraps the existing Green Agent episode manager with A2A protocol,
orchestrating assessments and producing task updates and artifacts.
"""

import json
import traceback
from typing import Generator, Dict, Any, Optional
from datetime import datetime

from green_agent.green_healthcare_agent import GreenHealthcareAgent
from green_agent.protocol import parse_action_from_text
from .models import AssessmentRequest, TaskUpdate, Artifact
from .a2a_client import A2AClient


class GreenExecutor:
    """
    A2A-compliant Green Executor for MedAgentBench assessments.

    This executor wraps the existing GreenHealthcareAgent and provides
    A2A protocol compliance, including:
    - Assessment request handling
    - Task update streaming
    - Purple agent communication
    - Artifact generation
    """

    def __init__(self):
        """Initialize the Green Executor."""
        self.agent: Optional[GreenHealthcareAgent] = None
        self.purple_client: Optional[A2AClient] = None
        self.current_task_id: Optional[str] = None

    def run_assessment(
        self,
        assessment_request: AssessmentRequest
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Run a complete assessment episode with a purple agent.

        This is the main entry point for A2A assessments. It:
        1. Initializes the green agent
        2. Connects to the purple agent
        3. Runs the episode
        4. Streams task updates
        5. Returns final artifact

        Args:
            assessment_request: The A2A assessment request

        Yields:
            Task updates and final artifact as dictionaries

        Raises:
            RuntimeError: If assessment fails
        """
        try:
            # Extract configuration
            config = assessment_request.config
            fhir_url = config.get("fhir_base_url", "http://localhost:8080/fhir")
            max_steps = config.get("max_steps", 8)
            task_id = config.get("task_id", None)

            # Get purple agent endpoint
            purple_endpoint = assessment_request.participants.get("purple_agent")
            if not purple_endpoint:
                raise ValueError("No purple_agent endpoint specified in participants")

            # Initialize green agent
            self.agent = GreenHealthcareAgent(
                fhir_base_url=fhir_url,
                max_steps=max_steps
            )

            # Initialize purple agent client
            self.purple_client = A2AClient(purple_endpoint)

            # Start episode
            initial_observation = self.agent.reset()
            self.current_task_id = self.agent.episode.task_id

            # Send initial task update
            yield self._create_task_update(
                step=0,
                max_steps=max_steps,
                status="Episode started",
                done=False,
                metadata={
                    "task_id": self.current_task_id,
                    "patient_id": self.agent.episode.patient_id,
                }
            ).dict()

            # Run episode loop
            done = False
            step = 0

            while not done and step < max_steps:
                step += 1

                # Send observation to purple agent
                try:
                    action_json = self.purple_client.send_observation(initial_observation)
                except Exception as e:
                    yield self._create_task_update(
                        step=step,
                        max_steps=max_steps,
                        status=f"Purple agent communication error: {str(e)}",
                        done=True,
                        metadata={"error": str(e)}
                    ).dict()
                    break

                # Parse action
                try:
                    action = parse_action_from_text(action_json)
                except Exception as e:
                    yield self._create_task_update(
                        step=step,
                        max_steps=max_steps,
                        status=f"Invalid action from purple agent: {str(e)}",
                        done=True,
                        metadata={"error": str(e), "action_json": action_json}
                    ).dict()
                    break

                # Send task update about the action
                action_type = action.action if hasattr(action, 'action') else str(type(action).__name__)
                status_msg = f"Step {step}: {action_type}"
                if hasattr(action, 'tool_name') and action.tool_name:
                    status_msg += f" - {action.tool_name}"

                yield self._create_task_update(
                    step=step,
                    max_steps=max_steps,
                    status=status_msg,
                    done=False,
                    metadata={
                        "action_type": action_type,
                        "tool_name": getattr(action, 'tool_name', None),
                    }
                ).dict()

                # Execute action via green agent
                observation, reward, done, info = self.agent.step(action_json)
                initial_observation = observation

                # If done, send completion update
                if done:
                    yield self._create_task_update(
                        step=step,
                        max_steps=max_steps,
                        status="Episode completed",
                        done=True,
                        metadata={
                            "reward": reward,
                            "info": info,
                        }
                    ).dict()

            # Generate final artifact
            artifact = self._create_evaluation_artifact(
                task_id=self.current_task_id,
                patient_id=self.agent.episode.patient_id,
                final_info=info if done else {},
                total_steps=step
            )

            yield artifact.dict()

        except Exception as e:
            # Send error artifact
            error_artifact = Artifact(
                artifact_type="evaluation_error",
                content={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "task_id": self.current_task_id,
                }
            )
            yield error_artifact.dict()

        finally:
            # Cleanup
            if self.purple_client:
                self.purple_client.close()

    def _create_task_update(
        self,
        step: int,
        max_steps: int,
        status: str,
        done: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskUpdate:
        """
        Create a task update message.

        Args:
            step: Current step number
            max_steps: Maximum number of steps
            status: Status message
            done: Whether the episode is complete
            metadata: Optional metadata

        Returns:
            TaskUpdate object
        """
        return TaskUpdate(
            step=step,
            max_steps=max_steps,
            status=status,
            done=done,
            metadata=metadata or {}
        )

    def _create_evaluation_artifact(
        self,
        task_id: str,
        patient_id: str,
        final_info: Dict[str, Any],
        total_steps: int
    ) -> Artifact:
        """
        Create the final evaluation artifact.

        Args:
            task_id: MedAgentBench task ID
            patient_id: Patient MRN
            final_info: Final info from episode (includes evaluation results)
            total_steps: Total number of steps taken

        Returns:
            Artifact containing evaluation results
        """
        # Extract evaluation results
        evaluation = final_info.get("evaluation", {})

        content = {
            "task_id": task_id,
            "patient_id": patient_id,
            "total_steps": total_steps,
            "evaluation": {
                "correct": evaluation.get("correct", False),
                "extracted_answer": evaluation.get("extracted_answer"),
                "error": evaluation.get("error"),
            },
            "final_summary": final_info.get("final_summary"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add score (1.0 if correct, 0.0 otherwise)
        content["score"] = 1.0 if evaluation.get("correct") else 0.0

        return Artifact(
            artifact_type="evaluation_result",
            content=content
        )
