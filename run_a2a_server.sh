#!/bin/bash
set -e

echo "=========================================="
echo "MedAgentBench A2A Green Agent"
echo "=========================================="

# Parse command line arguments
HOST="0.0.0.0"
PORT="8000"
CARD_URL=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --card-url)
      CARD_URL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH
echo "PYTHONPATH set to: $PYTHONPATH"

# Check if FHIR server is accessible (if running in Docker Compose)
if [ ! -z "$FHIR_BASE_URL" ]; then
    FHIR_URL="${FHIR_BASE_URL}"
else
    FHIR_URL="http://localhost:8080/fhir"
fi

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
    echo "Continuing anyway - FHIR server may be on a different network"
fi

# Start the A2A Green Agent server
echo ""
echo "=========================================="
echo "Starting A2A Green Agent Server"
echo "=========================================="
echo "The API will be available at: http://$HOST:$PORT"
echo "Agent card at: http://$HOST:$PORT/card"
echo "Assessment endpoint at: http://$HOST:$PORT/assess"
echo "API documentation at: http://$HOST:$PORT/docs"
if [ ! -z "$CARD_URL" ]; then
    echo "Card URL: $CARD_URL"
fi
echo ""

# Build python command
CMD="python -m src.a2a_adapter --host $HOST --port $PORT"
if [ ! -z "$CARD_URL" ]; then
    CMD="$CMD --card-url $CARD_URL"
fi

exec $CMD
