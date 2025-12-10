"""
Example Purple Agent - Demonstrates how to connect to the Green Healthcare Agent

This is a minimal example showing how a Purple Agent (the agent being evaluated)
should interact with the Green Agent over HTTP.

The Purple Agent needs to:
1. Call POST /reset to start a new episode
2. Parse the observation from the Green Agent
3. Decide on an action (call a tool or finish)
4. Send the action as JSON to POST /step
5. Repeat until the episode is done

This example implements a simple random agent for demonstration purposes.
Real Purple Agents should use LLMs or other intelligent decision-making.
"""

import requests
import json
import random


class PurpleAgentClient:
    """
    Client for interacting with the Green Healthcare Agent API.
    """

    def __init__(self, base_url="http://localhost:8000"):
        """
        Initialize the Purple Agent client.

        Args:
            base_url: Base URL of the Green Agent API (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def reset(self):
        """
        Start a new episode.

        Returns:
            str: The initial prompt/observation from the Green Agent
        """
        response = self.session.post(f"{self.base_url}/reset", json={})
        response.raise_for_status()
        data = response.json()
        return data["prompt"]

    def step(self, agent_response):
        """
        Take a step in the episode.

        Args:
            agent_response: JSON string containing the agent's action

        Returns:
            tuple: (prompt, reward, done, info)
        """
        response = self.session.post(
            f"{self.base_url}/step",
            json={"agent_response": agent_response}
        )
        response.raise_for_status()
        data = response.json()
        return data["prompt"], data["reward"], data["done"], data["info"]


class SimpleRandomPurpleAgent:
    """
    A simple random Purple Agent for demonstration.

    This agent randomly chooses actions. Real agents should use LLMs
    or other intelligent methods to parse observations and make decisions.
    """

    def __init__(self):
        self.available_tools = []
        self.patient_id = None
        self.step_count = 0

    def parse_observation(self, prompt):
        """
        Parse the observation from the Green Agent.

        In a real agent, you would parse the JSON observation from the prompt.
        This example does a simple extraction.

        Args:
            prompt: The prompt text from the Green Agent
        """
        # Extract JSON from prompt (it's embedded in the text)
        try:
            # Find JSON in the prompt
            json_start = prompt.find('{')
            json_end = prompt.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                obs_json = prompt[json_start:json_end]
                obs = json.loads(obs_json)

                # Extract available tools
                self.available_tools = [tool["name"] for tool in obs.get("available_tools", [])]

                # Extract patient ID from task description
                task_desc = obs.get("task_description", "")
                if "MRN:" in task_desc:
                    # Simple extraction
                    lines = task_desc.split('\n')
                    for line in lines:
                        if "Patient MRN:" in line:
                            self.patient_id = line.split(":")[-1].strip()

                self.step_count = obs.get("step", 0)

        except Exception as e:
            print(f"Warning: Failed to parse observation: {e}")

    def decide_action(self):
        """
        Decide what action to take.

        Returns:
            str: JSON string representing the action

        In this simple example, we randomly choose to either:
        - Call a tool (with random parameters)
        - Finish (after a few steps)
        """

        # After 3 steps, randomly decide to finish
        if self.step_count >= 3 and random.random() < 0.5:
            action = {
                "action": "finish",
                "final_summary": "Based on the available information, I have completed my analysis. Patient requires further evaluation."
            }
            return json.dumps(action)

        # Otherwise, call a random tool
        if self.available_tools and self.patient_id:
            # Pick a random tool
            tool_name = random.choice(self.available_tools)

            # Create appropriate arguments based on tool
            if tool_name == "get_patient_basic":
                arguments = {"patient_id": self.patient_id}
            elif tool_name == "get_recent_labs":
                arguments = {
                    "patient_id": self.patient_id,
                    "lab_code": random.choice(["Hb", "GLU", "Cr", "K", "MG"])
                }
            elif tool_name in ["get_conditions", "search_encounters", "search_medications",
                               "search_procedures", "search_diagnostic_reports"]:
                arguments = {"patient_id": self.patient_id}
            elif tool_name == "search_observations":
                arguments = {
                    "patient_id": self.patient_id,
                    "category": random.choice(["vital-signs", "laboratory"])
                }
            else:
                arguments = {"patient_id": self.patient_id}

            action = {
                "action": "call_tool",
                "tool_name": tool_name,
                "arguments": arguments
            }
            return json.dumps(action)

        # Fallback: finish
        action = {
            "action": "finish",
            "final_summary": "Unable to proceed. Finishing episode."
        }
        return json.dumps(action)


def run_simple_episode():
    """
    Run a complete episode with the simple random agent.
    """
    print("=" * 60)
    print("Purple Agent Example - Running Episode")
    print("=" * 60)

    # Initialize client and agent
    client = PurpleAgentClient(base_url="http://localhost:8000")
    agent = SimpleRandomPurpleAgent()

    # Start episode
    print("\n[1] Calling /reset to start episode...")
    prompt = client.reset()
    print(f"Received initial prompt ({len(prompt)} chars)")
    print(f"First 200 chars: {prompt[:200]}...")

    # Parse initial observation
    agent.parse_observation(prompt)
    print(f"\nDetected {len(agent.available_tools)} available tools")
    print(f"Patient ID: {agent.patient_id}")

    # Run episode loop
    done = False
    step = 0
    max_steps = 8

    while not done and step < max_steps:
        step += 1
        print(f"\n[{step + 1}] Agent deciding action...")

        # Decide action
        action_json = agent.decide_action()
        action = json.loads(action_json)
        print(f"Action: {action['action']}")
        if action['action'] == 'call_tool':
            print(f"  Tool: {action['tool_name']}")
            print(f"  Args: {action['arguments']}")
        else:
            print(f"  Summary: {action['final_summary'][:100]}...")

        # Send action to Green Agent
        print(f"Calling /step...")
        prompt, reward, done, info = client.step(action_json)

        print(f"Response - Reward: {reward}, Done: {done}")
        if done:
            print(f"\n=== Episode Complete ===")
            print(f"Info: {json.dumps(info, indent=2)}")
        else:
            print(f"Observation preview: {prompt[:200]}...")
            # Parse new observation
            agent.parse_observation(prompt)

    print("\n" + "=" * 60)
    print("Episode finished!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Example Purple Agent")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Green Agent API URL (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    # Check if Green Agent is reachable
    try:
        response = requests.get(f"{args.url}/health", timeout=5)
        response.raise_for_status()
        print(f"✓ Green Agent is reachable at {args.url}")
    except Exception as e:
        print(f"✗ Cannot reach Green Agent at {args.url}")
        print(f"Error: {e}")
        print("\nPlease ensure the Green Agent is running:")
        print("  docker-compose up")
        print("  or")
        print("  python green_agent_server.py")
        exit(1)

    # Run episode
    run_simple_episode()
