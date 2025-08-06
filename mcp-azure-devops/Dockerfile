FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY . /app
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Set environment variables (should be overridden at runtime)
ENV AZURE_DEVOPS_PAT=""
ENV AZURE_DEVOPS_ORGANIZATION_URL=""

# Expose a default port (change as needed)
EXPOSE 8000

# Default command (adjust to your server start command)
CMD ["python", "src/mcp_azure_devops/server.py"]
