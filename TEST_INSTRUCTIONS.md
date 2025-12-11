# Test Instructions for A2A Green Agent

## Quick Test (30 seconds)

```bash
# 1. Build and start
docker-compose -f docker-compose.a2a.yml up --build

# 2. Wait for "Starting A2A Green Agent Server" message

# 3. In another terminal, test health
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"medagentbench-a2a-green-agent"}

# 4. Test agent card
curl http://localhost:8000/card
# Expected: JSON with agent metadata

# SUCCESS! ✓
```

---

## Complete Test Suite

### Prerequisites

```bash
# Ensure Docker is running
docker ps

# Ensure ports are free
lsof -i :8000 -i :8080
# Should be empty
```

---

### Test 1: Docker Build

```bash
# Build for linux/amd64
docker build --platform linux/amd64 -t medagent-green:test .

# Verify build
docker images | grep medagent-green

# Expected output:
# medagent-green    test    <image-id>    <timestamp>    <size>
```

**Expected Result**: ✓ Image builds without errors

---

### Test 2: Start Services (A2A Mode)

```bash
# Start with A2A docker-compose
docker-compose -f docker-compose.a2a.yml up
```

**Expected Logs**:
```
✓ FHIR server is ready
Starting A2A Green Agent Server
The API will be available at: http://0.0.0.0:8000
Agent card: http://0.0.0.0:8000/card
Assessment endpoint: http://0.0.0.0:8000/assess
```

**Expected Result**: ✓ Both containers start without errors

---

### Test 3: Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "medagentbench-a2a-green-agent"
}
```

**Expected Result**: ✓ HTTP 200, correct JSON

---

### Test 4: Agent Card

```bash
curl http://localhost:8000/card | jq
```

**Expected Response**:
```json
{
  "name": "MedAgentBench Green Agent",
  "version": "1.0.0",
  "description": "A2A-compliant Green Agent for evaluating healthcare AI agents using MedAgentBench tasks",
  "capabilities": {
    "protocol": "a2a",
    "streaming": true,
    "evaluation": true
  },
  "config_schema": { ... },
  "required_participants": ["purple_agent"],
  "produces_artifacts": true,
  "artifact_types": ["evaluation_result", "evaluation_error"]
}
```

**Expected Result**: ✓ HTTP 200, valid agent card

---

### Test 5: API Documentation

```bash
# Open in browser
open http://localhost:8000/docs
# Or:
curl http://localhost:8000/docs
```

**Expected Result**: ✓ FastAPI interactive documentation loads

---

### Test 6: Assessment Request (Will Fail - No Purple Agent)

```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{
    "participants": {
      "purple_agent": "http://mock-purple:8001"
    },
    "config": {
      "fhir_base_url": "http://fhir-server:8080/fhir",
      "max_steps": 8
    }
  }'
```

**Expected Response** (streaming):
```json
{"type":"task_update","timestamp":"...","step":0,"max_steps":8,"status":"Episode started","done":false,"metadata":{...}}
{"type":"task_update","timestamp":"...","step":1,"max_steps":8,"status":"Purple agent communication error: ...","done":true,"metadata":{...}}
{"type":"artifact","artifact_type":"evaluation_result","content":{...}}
```

**Expected Result**: ✓ Stream starts, fails gracefully with error message about unreachable purple agent

---

### Test 7: Legacy Mode (Backward Compatibility)

```bash
# Stop A2A mode
docker-compose -f docker-compose.a2a.yml down

# Start legacy mode
docker-compose up

# In another terminal
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{}'
```

**Expected Response**:
```json
{
  "prompt": "...",
  "message": "Episode started successfully"
}
```

**Expected Result**: ✓ Legacy mode still works

---

### Test 8: Example Purple Agent (End-to-End)

```bash
# With services running (A2A mode):
docker-compose -f docker-compose.a2a.yml up -d

# Run example purple agent
python examples/purple_agent_example.py
```

**Expected Output**:
```
✓ Green Agent is reachable at http://localhost:8000
...
Detected 9 available tools
Patient ID: S<numbers>
...
Episode finished!
```

**Expected Result**: ✓ Complete episode runs successfully

**Note**: This uses legacy mode (`/reset`, `/step`), not A2A mode

---

### Test 9: Local Development (Without Docker)

```bash
# Terminal 1: FHIR Server
docker run -d -p 8080:8080 jyxsu6/medagentbench:latest

# Terminal 2: A2A Server
export PYTHONPATH=/path/to/green-medagentbench:$PYTHONPATH
python -m src.a2a_adapter.a2a_green_server --host 0.0.0.0 --port 8000

# Terminal 3: Test
curl http://localhost:8000/health
```

**Expected Result**: ✓ Server starts and responds

---

### Test 10: Docker Run with Arguments

```bash
# Stop docker-compose
docker-compose -f docker-compose.a2a.yml down

# Run manually with custom arguments
docker run -d \
  -p 8000:8000 \
  --name test-green-agent \
  medagent-green:test \
  --host 0.0.0.0 \
  --port 8000 \
  --card-url http://example.com/card

# Check logs
docker logs test-green-agent

# Test
curl http://localhost:8000/health

# Cleanup
docker stop test-green-agent
docker rm test-green-agent
```

**Expected Result**: ✓ Arguments parsed correctly, server starts

---

## Debugging Tests

### If Health Check Fails

```bash
# Check container status
docker ps -a

# Check logs
docker logs green-medagentbench-green-agent-a2a-1

# Check if port is bound
lsof -i :8000

# Try rebuilding
docker-compose -f docker-compose.a2a.yml up --build --force-recreate
```

### If FHIR Server Not Ready

```bash
# Check FHIR container
docker logs green-medagentbench-fhir-server-1

# Wait for: "Started Application in XXX seconds"

# Test FHIR directly
curl http://localhost:8080/fhir/metadata
```

### If Import Errors

```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Should include: /path/to/green-medagentbench

# Fix:
export PYTHONPATH=/path/to/green-medagentbench:$PYTHONPATH
```

---

## Performance Tests

### Response Time

```bash
time curl http://localhost:8000/health
```

**Expected**: < 100ms

### Concurrent Requests

```bash
# Install hey: https://github.com/rakyll/hey
# Or use apache bench (ab)

hey -n 100 -c 10 http://localhost:8000/health
```

**Expected**: All requests succeed

### Memory Usage

```bash
docker stats green-medagentbench-green-agent-a2a-1
```

**Expected**: < 500MB

---

## Validation Checklist

### A2A Compliance

- [x] Accepts AssessmentRequest with participants and config
- [x] Returns streaming NDJSON responses
- [x] Produces TaskUpdate messages
- [x] Produces final Artifact
- [x] Agent card endpoint works
- [x] Health check endpoint works
- [x] Handles purple agent communication errors gracefully
- [x] ENTRYPOINT accepts --host, --port, --card-url
- [x] Built for linux/amd64

### Backward Compatibility

- [x] Legacy /reset endpoint still works
- [x] Legacy /step endpoint still works
- [x] Original docker-compose.yml still works
- [x] Example purple agent still works
- [x] No changes to green_agent/ directory
- [x] No changes to scoring logic

### Documentation

- [x] README has Quickstart guide
- [x] README has A2A usage examples
- [x] README has Docker instructions
- [x] README has troubleshooting section
- [x] Scenario.toml is complete and valid
- [x] Code is well-commented

---

## AgentBeats Integration Test

### Prerequisites

```bash
# Install AgentBeats CLI
uv tool install agentbeats
```

### Run Scenario

```bash
# Edit scenario.toml to point to a real purple agent
vim scenarios/medagent/scenario.toml

# Run assessment
uv run agentbeats-run scenarios/medagent/scenario.toml
```

**Expected Output**:
- Assessment starts
- Task updates stream
- Final artifact with evaluation results
- Results saved to ./results/

**Note**: Requires a working purple agent implementation

---

## Success Criteria

✓ All 10 tests pass
✓ No errors in Docker logs
✓ Health check returns 200
✓ Agent card is valid
✓ Streaming works (NDJSON)
✓ Legacy mode preserved
✓ Documentation complete

---

## Common Issues & Solutions

### Issue: "Port already in use"

```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port
docker-compose -f docker-compose.a2a.yml up -e GREEN_AGENT_HOST_PORT=8001
```

### Issue: "Module not found: fastapi"

```bash
# In Docker: Rebuild
docker-compose -f docker-compose.a2a.yml up --build

# Locally: Install dependencies
pip install -r requirements.txt
```

### Issue: "FHIR server connection refused"

```bash
# Wait longer (FHIR takes ~30 seconds to start)
# Or check if FHIR container is running:
docker ps | grep fhir
```

### Issue: "Purple agent communication error"

**Expected**: This is normal if no purple agent is running
**Solution**: Implement and start a purple agent, or use legacy mode for testing

---

## Next Steps After Testing

1. ✓ All tests pass → Push Docker image
2. ✓ Documentation complete → Update GitHub repo
3. ✓ Backward compatibility verified → Announce to users
4. ✓ A2A compliance confirmed → Register with AgentBeats

---

**Happy Testing! 🧪**
