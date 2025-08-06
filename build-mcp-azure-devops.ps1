# PowerShell script to clone the repository, create a Dockerfile, and build the Docker image
# Environment variables: AZURE_DEVOPS_PAT and AZURE_DEVOPS_ORGANIZATION_URL

# Variables
$imageName = "mcp-azure-devops:latest"

# Create Dockerfile
$dockerfileContent = @"
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
"@

$dockerfilePath = "Dockerfile"
$dockerfileContent | Set-Content -Path $dockerfilePath -Force

# Build the Docker image
docker build -t $imageName .

Write-Host "Docker image '$imageName' built successfully."
Write-Host "To run the container, use:"
Write-Host "  docker run -e AZURE_DEVOPS_PAT=your_token -e AZURE_DEVOPS_ORGANIZATION_URL=your_org_url -p 8000:8000 $imageName"
