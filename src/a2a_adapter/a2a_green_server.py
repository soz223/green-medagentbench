"""
A2A Green Agent HTTP Server for MedAgentBench.

This module provides the HTTP server interface for the A2A-compliant
Green Agent, handling assessment requests and streaming responses.
"""

import json
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .models import AssessmentRequest, A2AResponse
from .green_executor import GreenExecutor


def create_app() -> FastAPI:
    """
    Create and configure the A2A Green Agent FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="MedAgentBench A2A Green Agent",
        description="A2A-compliant Green Agent for MedAgentBench healthcare assessments",
        version="1.0.0"
    )

    # ==================== Health Check ====================

    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "medagentbench-a2a-green-agent"}

    # ==================== Agent Card ====================

    @app.get("/card")
    def get_agent_card():
        """
        Return the agent card describing this Green Agent.

        The agent card provides metadata about the agent's capabilities,
        configuration, and requirements.
        """
        return {
            "name": "MedAgentBench Green Agent",
            "version": "1.0.0",
            "description": "A2A-compliant Green Agent for evaluating healthcare AI agents using MedAgentBench tasks",
            "capabilities": {
                "protocol": "a2a",
                "streaming": True,
                "evaluation": True,
            },
            "config_schema": {
                "type": "object",
                "properties": {
                    "fhir_base_url": {
                        "type": "string",
                        "description": "Base URL of the FHIR server",
                        "default": "http://localhost:8080/fhir"
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum number of steps per episode",
                        "default": 8
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Specific task ID to run (optional, random if not specified)"
                    }
                }
            },
            "required_participants": ["purple_agent"],
            "produces_artifacts": True,
            "artifact_types": ["evaluation_result", "evaluation_error"]
        }

    # ==================== Assessment Endpoint ====================

    @app.post("/assess")
    async def assess(request: AssessmentRequest):
        """
        Start a new assessment with the specified purple agent.

        This endpoint:
        1. Validates the assessment request
        2. Creates a new assessment session
        3. Streams task updates and final artifact

        The response is a stream of newline-delimited JSON objects:
        - Task updates (type: "task_update")
        - Final artifact (type: "artifact")

        Args:
            request: Assessment request with participants and config

        Returns:
            Streaming response with task updates and artifact
        """
        # Validate participants
        if "purple_agent" not in request.participants:
            raise HTTPException(
                status_code=400,
                detail="Missing required participant: purple_agent"
            )

        # Create executor and run assessment
        executor = GreenExecutor()

        def generate():
            """Generator function for streaming responses."""
            try:
                for update in executor.run_assessment(request):
                    # Send as newline-delimited JSON
                    yield json.dumps(update) + "\n"
            except Exception as e:
                # Send error as final artifact
                error_artifact = {
                    "type": "artifact",
                    "artifact_type": "evaluation_error",
                    "content": {
                        "error": str(e),
                        "message": "Assessment failed"
                    }
                }
                yield json.dumps(error_artifact) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson"
        )

    # ==================== Direct Evaluation Endpoint (Legacy) ====================

    class EvaluationRequest(BaseModel):
        """Legacy evaluation request (for backward compatibility)."""
        purple_agent_url: str
        fhir_base_url: str = "http://localhost:8080/fhir"
        max_steps: int = 8
        task_id: str = None

    @app.post("/evaluate")
    async def evaluate(request: EvaluationRequest):
        """
        Legacy evaluation endpoint for backward compatibility.

        This endpoint provides a simpler interface that doesn't require
        the full A2A assessment request format.

        Args:
            request: Evaluation request

        Returns:
            Streaming response with evaluation results
        """
        # Convert to AssessmentRequest
        assessment_request = AssessmentRequest(
            participants={"purple_agent": request.purple_agent_url},
            config={
                "fhir_base_url": request.fhir_base_url,
                "max_steps": request.max_steps,
                "task_id": request.task_id,
            }
        )

        # Delegate to assess endpoint
        return await assess(assessment_request)

    return app


# ==================== Main Entry Point ====================

def main():
    """Main entry point for the A2A Green Agent server."""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="MedAgentBench A2A Green Agent Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--card-url", help="URL where this agent's card can be accessed (optional)")
    args = parser.parse_args()

    app = create_app()

    print(f"========================================")
    print(f"MedAgentBench A2A Green Agent")
    print(f"========================================")
    print(f"Starting server on {args.host}:{args.port}")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"Agent card: http://{args.host}:{args.port}/card")
    print(f"Assessment endpoint: http://{args.host}:{args.port}/assess")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    if args.card_url:
        print(f"Card URL: {args.card_url}")
    print(f"========================================")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
