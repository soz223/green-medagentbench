# MedAgentBench A2A Green Agent - Dockerfile
# A2A-compliant Green Agent for healthcare AI evaluation

FROM --platform=linux/amd64 python:3.9-slim

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
ENV PYTHONPATH=/app

# Expose the A2A Green Agent port
EXPOSE 8000

# Make the startup scripts executable
RUN chmod +x /app/run_a2a_server.sh
RUN chmod +x /app/run_green_agent.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# A2A-compliant entrypoint
# Accepts: --host, --port, --card-url
ENTRYPOINT ["/app/run_a2a_server.sh"]

# Default arguments (can be overridden)
CMD []
