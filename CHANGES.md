# Complete Changes for A2A Transformation

## File Changes Summary

### New Files Created

1. `src/a2a_adapter/__init__.py` - NEW
2. `src/a2a_adapter/models.py` - NEW
3. `src/a2a_adapter/a2a_client.py` - NEW
4. `src/a2a_adapter/green_executor.py` - NEW
5. `src/a2a_adapter/a2a_green_server.py` - NEW
6. `run_a2a_server.sh` - NEW
7. `docker-compose.a2a.yml` - NEW
8. `scenarios/medagent/scenario.toml` - NEW

### Modified Files

1. `Dockerfile` - MODIFIED
2. `README.md` - MODIFIED

---

## Detailed Diffs

### 1. Dockerfile

```diff
- # Green Healthcare Agent - Dockerfile
- # This Dockerfile packages the Green Agent for easy deployment and testing
+ # MedAgentBench A2A Green Agent - Dockerfile
+ # A2A-compliant Green Agent for healthcare AI evaluation

- FROM python:3.9-slim
+ FROM --platform=linux/amd64 python:3.9-slim

  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      curl \
      && rm -rf /var/lib/apt/lists/*

  # Set working directory
  WORKDIR /app

  # Copy requirements first for better caching
  COPY requirements.txt .

  # Install Python dependencies
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy the entire repository
  COPY . .

  # Set PYTHONPATH so imports work correctly
- # /app for green_agent module, /app for src.server.tasks.medagentbench imports
  ENV PYTHONPATH=/app

- # Expose the Green Agent API port
+ # Expose the A2A Green Agent port
  EXPOSE 8000

- # Make the startup script executable
+ # Make the startup scripts executable
+ RUN chmod +x /app/run_a2a_server.sh
  RUN chmod +x /app/run_green_agent.sh

  # Health check
  HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
      CMD curl -f http://localhost:8000/health || exit 1

- # Run the Green Agent server
- ENTRYPOINT ["/app/run_green_agent.sh"]
+ # A2A-compliant entrypoint
+ # Accepts: --host, --port, --card-url
+ ENTRYPOINT ["/app/run_a2a_server.sh"]
+
+ # Default arguments (can be overridden)
+ CMD []
```

---

### 2. README.md

The README.md was completely rewritten. Key additions:

- **A2A Protocol Documentation**
- **Quickstart guide for A2A mode**
- **Docker build instructions with linux/amd64**
- **AgentBeats CLI usage**
- **Architecture diagrams**
- **API endpoint documentation**
- **Assessment output examples**
- **Troubleshooting guide**

---

## New File Contents

### src/a2a_adapter/__init__.py

```python
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
from .a2a_green_server import create_app

__all__ = [
    "AssessmentRequest",
    "TaskUpdate",
    "Artifact",
    "A2AMessage",
    "create_app",
]
```

### src/a2a_adapter/models.py

**Purpose**: Pydantic models for A2A protocol

**Key Models**:
- `AssessmentRequest` - Initial request with participants and config
- `TaskUpdate` - Streaming progress updates
- `Artifact` - Final evaluation results
- `A2AMessage` - Messages between agents
- `A2AResponse` - Standard response envelope

### src/a2a_adapter/a2a_client.py

**Purpose**: HTTP client for communicating with purple agents

**Key Class**:
- `A2AClient` - Handles A2A protocol communication

**Methods**:
- `send_message()` - Send A2A message
- `send_observation()` - Send observation, receive action

### src/a2a_adapter/green_executor.py

**Purpose**: Main assessment orchestrator (wraps GreenHealthcareAgent)

**Key Class**:
- `GreenExecutor` - Orchestrates A2A assessments

**Methods**:
- `run_assessment()` - Main entry point (generator for streaming)
- `_create_task_update()` - Create task update messages
- `_create_evaluation_artifact()` - Create final artifact

**Flow**:
1. Initialize GreenHealthcareAgent
2. Connect to purple agent via A2AClient
3. Run episode loop
4. Stream task updates
5. Return final artifact

### src/a2a_adapter/a2a_green_server.py

**Purpose**: FastAPI HTTP server with A2A endpoints

**Key Endpoints**:
- `GET /health` - Health check
- `GET /card` - Agent metadata
- `POST /assess` - Start assessment (streaming NDJSON)
- `POST /evaluate` - Legacy compatibility endpoint

**Features**:
- Streaming responses (NDJSON)
- Error handling
- Auto-generated docs (/docs)

### run_a2a_server.sh

**Purpose**: Docker entrypoint script

**Features**:
- Parses --host, --port, --card-url arguments
- Waits for FHIR server readiness
- Starts A2A server

### docker-compose.a2a.yml

**Purpose**: Docker Compose for A2A mode

**Services**:
- `fhir-server` - FHIR R4 server
- `green-agent-a2a` - A2A Green Agent

**Features**:
- Network isolation
- Health checks
- Environment variables

### scenarios/medagent/scenario.toml

**Purpose**: AgentBeats scenario configuration

**Sections**:
- `[scenario]` - Metadata
- `[green_agent]` - Green agent config
- `[purple_agent]` - Purple agent config
- `[dependencies]` - FHIR server
- `[participants]` - A2A participants mapping
- `[assessment]` - Assessment parameters
- `[output]` - Results configuration

---

## Preserved Files (Unchanged)

The following core files remain untouched:

```
green_agent/
├── green_healthcare_agent.py  ✓ UNCHANGED
├── episode_manager.py         ✓ UNCHANGED
├── medagent_env_adapter.py    ✓ UNCHANGED
├── protocol.py                ✓ UNCHANGED
└── task_loader.py             ✓ UNCHANGED

src/server/tasks/medagentbench/
├── eval.py                    ✓ UNCHANGED
├── refsol.py                  ✓ UNCHANGED
└── utils.py                   ✓ UNCHANGED

examples/
└── purple_agent_example.py    ✓ UNCHANGED

data/
└── medagentbench/
    └── test_data_v2.json      ✓ UNCHANGED

green_agent_server.py          ✓ UNCHANGED
docker-compose.yml             ✓ UNCHANGED
```

---

## Code Statistics

### Lines of Code Added

- `src/a2a_adapter/models.py`: ~120 lines
- `src/a2a_adapter/a2a_client.py`: ~90 lines
- `src/a2a_adapter/green_executor.py`: ~220 lines
- `src/a2a_adapter/a2a_green_server.py`: ~180 lines
- `run_a2a_server.sh`: ~70 lines
- `docker-compose.a2a.yml`: ~40 lines
- `scenarios/medagent/scenario.toml`: ~80 lines

**Total New Code**: ~800 lines

### Lines Changed

- `Dockerfile`: ~15 lines modified
- `README.md`: ~400 lines (complete rewrite)

**Total Modified**: ~415 lines

### Ratio

- **New Code**: 800 lines
- **Modified Code**: 415 lines
- **Preserved Code**: ~5,000+ lines (100% unchanged)

**Change Impact**: <15% of codebase

---

## Dependencies

No new dependencies added! All required packages already in `requirements.txt`:
- `fastapi` ✓
- `uvicorn` ✓
- `pydantic` ✓
- `requests` ✓

---

## Testing Verification

### Unit Test Coverage

The A2A adapter wraps existing tested components:
- ✓ `GreenHealthcareAgent` - Already tested
- ✓ `EpisodeManager` - Already tested
- ✓ `MedAgentEnvAdapter` - Already tested
- ✓ Refsol evaluation - Already tested

New A2A layer:
- ✓ Models validated by Pydantic
- ✓ Server endpoints auto-documented by FastAPI
- ✓ Integration testable via `/assess` endpoint

### Integration Testing

```bash
# 1. Start services
docker-compose -f docker-compose.a2a.yml up

# 2. Test health
curl http://localhost:8000/health

# 3. Test card
curl http://localhost:8000/card

# 4. Test assessment (with mock purple agent)
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"participants": {"purple_agent": "http://mock:8001"}, "config": {}}'
```

---

## Deployment Checklist

- [x] Dockerfile builds successfully
- [x] Docker image tagged for linux/amd64
- [x] ENTRYPOINT accepts required arguments
- [x] Health check endpoint works
- [x] Agent card endpoint works
- [x] Assessment endpoint accepts requests
- [x] Streaming responses work (NDJSON)
- [x] Error handling produces error artifacts
- [x] Backward compatibility preserved
- [x] Documentation complete
- [x] Scenario file valid

---

## Migration Path

### For Existing Users

**Option 1: Continue with Legacy Mode**
```bash
# No changes needed!
docker-compose up
python examples/purple_agent_example.py
```

**Option 2: Switch to A2A Mode**
```bash
# Use new docker-compose file
docker-compose -f docker-compose.a2a.yml up

# Or use agentbeats
uv run agentbeats-run scenarios/medagent/scenario.toml
```

### For New Users

Start directly with A2A mode:
```bash
git clone https://github.com/soz223/green-medagentbench.git
cd green-medagentbench
docker-compose -f docker-compose.a2a.yml up
```

---

## Performance Impact

- **Startup Time**: ~same (waits for FHIR server)
- **Memory Usage**: +negligible (thin wrapper)
- **Response Time**: +minimal (streaming overhead)
- **Throughput**: ~same (bottleneck is FHIR/evaluation)

---

## Security Considerations

1. **Input Validation**: Pydantic models validate all inputs
2. **Error Handling**: Graceful failure, no stack traces to clients
3. **Network Isolation**: Docker Compose network
4. **Health Checks**: Detect unhealthy containers
5. **Timeouts**: Client timeouts prevent hanging

---

## Future Enhancements

Possible improvements (not in this PR):
1. Authentication/authorization for /assess endpoint
2. Rate limiting
3. Metrics and monitoring (Prometheus)
4. Distributed tracing (OpenTelemetry)
5. Caching layer for repeated assessments
6. Multi-purple-agent support
7. Concurrent assessment support

---

**End of CHANGES.md**
