#!/bin/bash
set -e

echo "=========================================="
echo "Starting Green Healthcare Agent"
echo "=========================================="

# Set PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH
echo "PYTHONPATH set to: $PYTHONPATH"

# Check if FHIR server is accessible
FHIR_URL="${FHIR_BASE_URL:-http://localhost:8080/fhir}"
echo ""
echo "Checking FHIR server at: $FHIR_URL"

MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f "$FHIR_URL/metadata" > /dev/null 2>&1; then
        echo "✓ FHIR server is ready"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for FHIR server... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "✗ FHIR server not accessible at $FHIR_URL"
    echo "Please ensure the FHIR server is running:"
    echo "  docker run -p 8080:8080 jyxsu6/medagentbench:latest"
    exit 1
fi

# Start the Green Agent HTTP API server
echo ""
echo "=========================================="
echo "Starting Green Agent API Server"
echo "=========================================="
echo "The API will be available at: http://0.0.0.0:8000"
echo "API documentation at: http://0.0.0.0:8000/docs"
echo ""

exec python green_agent_server.py --host 0.0.0.0 --port 8000
