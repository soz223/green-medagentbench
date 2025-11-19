"""
Smoke test for POST tool implementation.
Tests that POST tools work and history is formatted correctly.
"""
from green_agent.green_healthcare_agent import GreenHealthcareAgent
from green_agent.protocol import parse_action_from_text

# Create agent instance
agent = GreenHealthcareAgent(
    fhir_base_url="http://localhost:8080/fhir",
    max_steps=8
)

# Reset to start a new episode
print("=== Test 1: Reset and check initial state ===")
initial_prompt = agent.reset()
print(f"Initial prompt received (first 200 chars): {initial_prompt[:200]}...")
print()

# Test POST tool with a simple Observation creation
print("=== Test 2: Execute POST tool (create Observation) ===")
post_action_json = """
{
  "action": "call_tool",
  "tool_name": "post_fhir_resource",
  "arguments": {
    "resource_type": "Observation",
    "payload": {
      "resourceType": "Observation",
      "status": "final",
      "category": [{
        "coding": [{
          "system": "http://hl7.org/fhir/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }]
      }],
      "code": {"text": "BP"},
      "subject": {"reference": "Patient/S1234567"},
      "effectiveDateTime": "2023-11-13T10:15:00+00:00",
      "valueString": "118/77 mmHg"
    }
  }
}
"""

prompt, reward, done, info = agent.step(post_action_json)
print(f"Step result - reward: {reward}, done: {done}")
print(f"Info: {info}")
print(f"Next prompt (first 200 chars): {prompt[:200]}...")
print()

# Test 3: Check history in EpisodeManager
print("=== Test 3: Check history formatting ===")
history = agent.episode.history
print(f"Number of history items: {len(history)}")
for idx, item in enumerate(history):
    print(f"\nHistory item {idx}:")
    print(f"  Role: {item.role}")
    print(f"  Content (first 300 chars): {item.content[:300]}")

    # Check if POST is in the content
    if item.role == "agent" and "POST" in item.content:
        print(f"  ✓ Found POST in agent message")
        # Verify format matches what refsol expects
        lines = item.content.split('\n')
        if len(lines) >= 2 and lines[0].startswith("POST"):
            print(f"  ✓ Format appears correct: first line is POST URL")
            try:
                import json
                payload = json.loads('\n'.join(lines[1:]))
                print(f"  ✓ Payload is valid JSON with {len(payload)} fields")
            except:
                print(f"  ✗ Warning: Could not parse payload as JSON")

    if item.role == "user" and "POST request accepted" in item.content:
        print(f"  ✓ Found correct POST response message")

print()

# Test 4: Test refsol's extract_posts function with our history
print("=== Test 4: Test refsol's extract_posts compatibility ===")
try:
    from src.server.tasks.medagentbench.refsol import extract_posts, check_has_post

    # Create a mock results object with our history
    class MockResults:
        def __init__(self, history_items):
            self.history = history_items

    mock_results = MockResults(agent.episode.history)

    # Test check_has_post
    has_post = check_has_post(mock_results)
    print(f"check_has_post() result: {has_post}")
    if has_post:
        print("  ✓ refsol detected POST in history")
    else:
        print("  ✗ refsol did NOT detect POST (this is a problem)")

    # Test extract_posts
    posts = extract_posts(mock_results)
    print(f"\nextract_posts() found {len(posts)} POST(s)")
    for idx, (url, payload) in enumerate(posts):
        print(f"\n  POST {idx}:")
        print(f"    URL: {url}")
        print(f"    Payload type: {type(payload)}, keys: {list(payload.keys())[:5]}")
        if len(posts) > 0:
            print("  ✓ refsol successfully extracted POST from history")

except ImportError as e:
    print(f"Could not import refsol: {e}")
    print("This is expected if refsol module is not available")

print("\n=== Smoke test complete ===")
