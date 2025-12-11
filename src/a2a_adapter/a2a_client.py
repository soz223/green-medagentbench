"""
A2A Client for communicating with Purple Agents.

Handles HTTP communication with purple agents using the A2A protocol.
"""

import requests
import json
from typing import Dict, Any, Optional
from .models import A2AMessage


class A2AClient:
    """
    Client for sending A2A protocol messages to purple agents.

    This client handles HTTP communication with purple agents,
    sending observations and receiving actions.
    """

    def __init__(self, purple_agent_url: str, timeout: int = 30):
        """
        Initialize the A2A client.

        Args:
            purple_agent_url: Base URL of the purple agent's A2A endpoint
            timeout: Request timeout in seconds
        """
        self.purple_agent_url = purple_agent_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def send_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send an A2A message to the purple agent.

        Args:
            role: Role of the sender (typically 'green_agent')
            content: Message content (typically JSON observation)
            metadata: Optional metadata

        Returns:
            Response from the purple agent

        Raises:
            requests.RequestException: If the request fails
        """
        message = A2AMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        # Send to purple agent's A2A endpoint
        url = f"{self.purple_agent_url}/message"

        try:
            response = self.session.post(
                url,
                json=message.dict(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to communicate with purple agent at {url}: {e}")

    def send_observation(self, observation_json: str) -> str:
        """
        Send an observation to the purple agent and get back an action.

        Args:
            observation_json: JSON string containing the observation

        Returns:
            JSON string containing the purple agent's action

        Raises:
            RuntimeError: If communication fails
        """
        response = self.send_message(
            role="green_agent",
            content=observation_json,
            metadata={"type": "observation"}
        )

        # Extract action from response
        if "action" in response:
            return json.dumps(response["action"])
        elif "content" in response:
            return response["content"]
        else:
            raise RuntimeError(f"Invalid purple agent response: {response}")

    def close(self):
        """Close the HTTP session."""
        self.session.close()
