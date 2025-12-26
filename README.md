# MedAgentBench A2A Green Agent

> **A2A-compliant Green Agent for evaluating healthcare AI agents using MedAgentBench clinical tasks**

This repository provides an **AgentBeats A2A-compliant Green Agent** that evaluates healthcare AI agents (Purple Agents) on real-world clinical tasks using the MedAgentBench benchmark and FHIR (Fast Healthcare Interoperability Resources) data.

## 🌟 Features

- **A2A Protocol Support**: Full compliance with the Agent-to-Agent (A2A) protocol
- **MedAgentBench Tasks**: 300 real-world clinical evaluation tasks
- **FHIR Integration**: Authentic healthcare data via FHIR R4 server
- **Streaming Evaluation**: Real-time task updates during assessment
- **Automated Scoring**: Reference solution-based evaluation (refsol)
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Backward Compatible**: Legacy HTTP API still supported

---

## 🚀 Quickstart

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- (Optional) AgentBeats CLI: `uv tool install agentbeats`

### 1. Clone the Repository

```bash
git clone https://github.com/soz223/green-medagentbench.git
cd green-medagentbench
```

### 2. Start the Services

#### Option A: Using Docker Compose (A2A Mode)

```bash
# Start FHIR server + A2A Green Agent
docker-compose -f docker-compose.a2a.yml up
```

The Green Agent will be available at:
- **Health check**: http://localhost:8000/health
- **Agent card**: http://localhost:8000/card
- **Assessment endpoint**: http://localhost:8000/assess
- **API docs**: http://localhost:8000/docs

#### Option B: Using Docker Compose (Legacy Mode)

```bash
# Start FHIR server + Legacy Green Agent
docker-compose up
```

#### Option C: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start FHIR server only
docker run -d -p 8080:8080 jyxsu6/medagentbench:latest

# Run A2A Green Agent locally
python -m src.a2a_adapter.a2a_green_server --host 0.0.0.0 --port 8000
```

### 3. Run an Assessment

#### Using the AgentBeats CLI (Recommended)

```bash
# Run a scenario with agentbeats-run
uv run agentbeats-run scenarios/medagent/scenario.toml
```

#### Using Direct HTTP Request

```bash
# Send an assessment request
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{
    "participants": {
      "purple_agent": "http://your-purple-agent:8001"
    },
    "config": {
      "fhir_base_url": "http://localhost:8080/fhir",
      "max_steps": 8
    }
  }'
```

The response will be a stream of newline-delimited JSON with:
- **Task updates** (progress information)
- **Final artifact** (evaluation results)

#### Using Python Client

```python
import requests
import json

# Send assessment request
response = requests.post(
    "http://localhost:8000/assess",
    json={
        "participants": {
            "purple_agent": "http://your-purple-agent:8001"
        },
        "config": {
            "fhir_base_url": "http://localhost:8080/fhir",
            "max_steps": 8
        }
    },
    stream=True
)

# Stream responses
for line in response.iter_lines():
    if line:
        update = json.loads(line)
        print(f"Type: {update['type']}, Content: {update}")
```

---

## 📦 Docker Image

### Building the Image

```bash
# Build for linux/amd64
docker build --platform linux/amd64 -t ghcr.io/soz223/medagent-green:latest .

# Push to registry
docker push ghcr.io/soz223/medagent-green:latest
```

### Running the Image

```bash
# Run the Green Agent container
docker run -d \
  -p 8000:8000 \
  --name medagent-green \
  ghcr.io/soz223/medagent-green:latest \
  --host 0.0.0.0 \
  --port 8000
```

**Supported Arguments:**
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--card-url`: URL where the agent card can be accessed (optional)

---

## 🏗️ Architecture

### A2A Protocol Flow

```
┌─────────────────┐
│  Purple Agent   │
│  (Evaluated)    │
└────────┬────────┘
         │
         │ A2A Messages
         │
┌────────▼────────┐      ┌──────────────┐
│  Green Agent    │◄────►│ FHIR Server  │
│  (Evaluator)    │      │ (EHR Data)   │
└────────┬────────┘      └──────────────┘
         │
         │ Task Updates
         │ + Artifacts
         │
┌────────▼────────┐
│  Orchestrator   │
│  (AgentBeats)   │
└─────────────────┘
```

### Project Structure

```
green-medagentbench/
├── src/
│   └── a2a_adapter/              # A2A protocol implementation
│       ├── __init__.py
│       ├── models.py             # A2A data models
│       ├── a2a_client.py         # Purple agent client
│       ├── green_executor.py    # Assessment orchestrator
│       └── a2a_green_server.py  # HTTP server (FastAPI)
│
├── green_agent/                  # Core Green Agent logic (unchanged)
│   ├── green_healthcare_agent.py
│   ├── episode_manager.py
│   ├── medagent_env_adapter.py  # FHIR tools
│   ├── protocol.py
│   └── task_loader.py
│
├── src/server/tasks/medagentbench/  # Evaluation logic
│   ├── eval.py
│   ├── refsol.py                # Reference solutions
│   └── utils.py
│
├── data/medagentbench/           # Task data
│   └── test_data_v2.json        # 300 clinical tasks
│
├── scenarios/                    # AgentBeats scenarios
│   └── medagent/
│       └── scenario.toml
│
├── Dockerfile                    # A2A-compliant Docker image
├── docker-compose.yml           # Legacy mode
├── docker-compose.a2a.yml       # A2A mode
├── run_a2a_server.sh           # A2A entrypoint
└── README.md
```

---

## 🔌 API Endpoints

### A2A Mode

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/card` | GET | Agent card (metadata) |
| `/assess` | POST | Start A2A assessment (streaming) |
| `/docs` | GET | Interactive API documentation |

### Legacy Mode

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/reset` | POST | Start new episode |
| `/step` | POST | Execute agent action |

---

## 🎯 MedAgentBench Tasks

The Green Agent evaluates Purple Agents on 300 real-world clinical tasks across 8 categories:

1. **Task 1**: Patient information retrieval
2. **Task 2**: Age calculation
3. **Task 3**: Lab result interpretation
4. **Task 4**: Medication management
5. **Task 5**: Procedure ordering
6. **Task 6**: Diagnosis analysis
7. **Task 7**: Clinical referrals
8. **Task 8**: Multi-step clinical workflows

Each task:
- Uses real FHIR-compliant patient data
- Requires multi-step reasoning
- Evaluated with reference solutions (refsol)
- Scored as correct/incorrect

---

## 🛠️ Development

### Running Tests

```bash
# Run the example Purple Agent (random actions)
python examples/purple_agent_example.py
```

### Local A2A Development

```bash
# Terminal 1: Start FHIR server
docker run -p 8080:8080 jyxsu6/medagentbench:latest

# Terminal 2: Start Green Agent (A2A mode)
python -m src.a2a_adapter.a2a_green_server --host 0.0.0.0 --port 8000

# Terminal 3: Test assessment
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"participants": {"purple_agent": "http://localhost:8001"}, "config": {}}'
```

### Extending the Green Agent

The A2A adapter is a thin wrapper around the existing Green Agent. To modify evaluation logic:

1. **Add tools**: Edit `green_agent/medagent_env_adapter.py`
2. **Modify scoring**: Edit `src/server/tasks/medagentbench/refsol.py`
3. **Change task loading**: Edit `green_agent/task_loader.py`
4. **Update A2A behavior**: Edit `src/a2a_adapter/green_executor.py`

---

## 📊 Assessment Output

### Task Update (Streaming)

```json
{
  "type": "task_update",
  "timestamp": "2025-12-11T01:30:00.000Z",
  "step": 2,
  "max_steps": 8,
  "status": "Step 2: call_tool - get_patient_basic",
  "done": false,
  "metadata": {
    "action_type": "call_tool",
    "tool_name": "get_patient_basic"
  }
}
```

### Final Artifact

```json
{
  "type": "artifact",
  "artifact_type": "evaluation_result",
  "content": {
    "task_id": "task1_5",
    "patient_id": "S1234567",
    "total_steps": 4,
    "evaluation": {
      "correct": true,
      "extracted_answer": ["42"],
      "error": null
    },
    "final_summary": "Patient age is 42 years old.",
    "score": 1.0,
    "timestamp": "2025-12-11T01:30:15.000Z"
  },
  "timestamp": "2025-12-11T01:30:15.000Z"
}
```

---

## 🔐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FHIR_BASE_URL` | FHIR server URL | `http://localhost:8080/fhir` |
| `FHIR_HOST_PORT` | FHIR server host port | `8080` |
| `GREEN_AGENT_HOST_PORT` | Green Agent host port | `8000` |

---

## 🐛 Troubleshooting

### FHIR Server Not Ready

If you see "Waiting for FHIR server...", ensure the FHIR server is running:

```bash
docker ps | grep medagentbench
```

### Purple Agent Connection Failed

Ensure your Purple Agent:
1. Is running and accessible
2. Implements the A2A protocol
3. Responds to `/message` endpoint
4. Returns valid JSON actions

### Import Errors

Ensure `PYTHONPATH` is set correctly:

```bash
export PYTHONPATH=/path/to/green-medagentbench:$PYTHONPATH
```

---

## 📚 References

- **MedAgentBench Paper**: [Link to paper]
- **FHIR R4 Specification**: https://www.hl7.org/fhir/
- **AgentBeats Documentation**: [Link to AgentBeats docs]
- **A2A Protocol**: [Link to A2A spec]

---

## 📄 License

[Specify your license]

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📧 Contact

- **Maintainer**: [Your name]
- **Repository**: https://github.com/soz223/green-medagentbench
- **Issues**: https://github.com/soz223/green-medagentbench/issues

---

## 🙏 Acknowledgments

- MedAgentBench team for the benchmark tasks
- HAPI FHIR for the FHIR server
- AgentBeats team for the A2A protocol
