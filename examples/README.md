# Purple Agent Examples

This directory contains example implementations showing how Purple Agents (the agents being evaluated) should connect to and interact with the Green Healthcare Agent.

## Quick Start

1. **Start the Green Agent:**
   ```bash
   # From the repository root
   docker-compose up
   ```

2. **Run the example Purple Agent:**
   ```bash
   python examples/purple_agent_example.py
   ```

## What the Example Shows

The `purple_agent_example.py` demonstrates:

- **API Connection**: How to connect to the Green Agent HTTP API
- **Episode Lifecycle**: The complete reset → step → finish flow
- **Observation Parsing**: How to extract information from the Green Agent's observations
- **Action Formatting**: Correct JSON format for tool calls and finish actions
- **Tool Usage**: Examples of calling different medical tools with proper arguments

## Building Your Own Purple Agent

To create your own Purple Agent:

1. **Connect to the API**: Use the `PurpleAgentClient` class or implement your own HTTP client
2. **Start an episode**: Call `POST /reset`
3. **Parse observations**: Extract task description, available tools, patient ID, and previous results
4. **Make intelligent decisions**: Use an LLM or other AI to decide which tools to call
5. **Format actions correctly**:
   - Tool call: `{"action": "call_tool", "tool_name": "...", "arguments": {...}}`
   - Finish: `{"action": "finish", "final_summary": "..."}`
6. **Submit actions**: Call `POST /step` with your action
7. **Repeat**: Continue until the episode is done (max 8 steps)

## Important Notes

- **Patient ID**: Most tools require a `patient_id` argument (the patient's MRN). Extract this from the task description.
- **JSON Format**: All actions must be valid JSON. The Green Agent will reject malformed JSON with an error message.
- **Medical Context**: This is a medical evaluation environment. Real agents should make clinically sound decisions, not random choices.
- **Tool Restrictions**: Some tasks prohibit certain actions (e.g., no POST operations). Violating these restrictions results in incorrect evaluation.

## API Reference

See the main [README.md](../README.md) for complete API documentation.

## Need Help?

- Check the interactive API docs at http://localhost:8000/docs when the Green Agent is running
- Review the main README for troubleshooting tips
- Examine the example code for implementation details
