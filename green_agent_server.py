"""
Simple HTTP API server for the Green Healthcare Agent.

This server exposes the Green Agent as a REST API so Purple Agents can connect
and interact with it over HTTP.

Endpoints:
- POST /reset - Start a new episode
- POST /step - Take a step in the current episode
- GET /health - Health check endpoint
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn

from green_agent.green_healthcare_agent import GreenHealthcareAgent

app = FastAPI(title="Green Healthcare Agent API")

# Global agent instance
agent = None


class ResetRequest(BaseModel):
    """Request to reset/start a new episode."""
    task_id: str = None  # Optional: specify a specific task ID
    fhir_base_url: str = "http://localhost:8080/fhir"
    max_steps: int = 8


class ResetResponse(BaseModel):
    """Response from reset endpoint."""
    prompt: str
    message: str = "Episode started successfully"


class StepRequest(BaseModel):
    """Request to take a step in the episode."""
    agent_response: str  # The Purple Agent's JSON response


class StepResponse(BaseModel):
    """Response from step endpoint."""
    prompt: str
    reward: float
    done: bool
    info: Dict[str, Any]


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "green-healthcare-agent"}


@app.post("/reset", response_model=ResetResponse)
def reset_episode(request: ResetRequest):
    """
    Start a new episode.

    This initializes the Green Agent with a new task from MedAgentBench.
    Returns the initial prompt that should be sent to the Purple Agent.
    """
    global agent

    try:
        # Create new agent instance with specified parameters
        agent = GreenHealthcareAgent(
            fhir_base_url=request.fhir_base_url,
            max_steps=request.max_steps
        )

        # Reset the agent (loads a random task)
        # TODO: Support task_id parameter if provided
        prompt = agent.reset()

        return ResetResponse(prompt=prompt)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset episode: {str(e)}")


@app.post("/step", response_model=StepResponse)
def step_episode(request: StepRequest):
    """
    Take a step in the current episode.

    The Purple Agent sends its action (as JSON text), and the Green Agent
    executes it and returns the next observation.
    """
    global agent

    if agent is None:
        raise HTTPException(
            status_code=400,
            detail="No active episode. Please call /reset first."
        )

    try:
        # Execute the step
        prompt, reward, done, info = agent.step(request.agent_response)

        return StepResponse(
            prompt=prompt,
            reward=reward,
            done=done,
            info=info
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute step: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Green Healthcare Agent HTTP API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting Green Healthcare Agent API server on {args.host}:{args.port}")
    print(f"API docs available at http://{args.host}:{args.port}/docs")

    uvicorn.run(app, host=args.host, port=args.port)
