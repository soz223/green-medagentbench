# Green Healthcare Agent - Dockerfile
# This Dockerfile packages the Green Agent for easy deployment and testing

FROM python:3.9-slim

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
ENV PYTHONPATH=/app:/app/src

# Expose the Green Agent API port
EXPOSE 8000

# Make the startup script executable
RUN chmod +x /app/run_green_agent.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the Green Agent server
ENTRYPOINT ["/app/run_green_agent.sh"]
