# PowerShell script to clone the repository, create a Dockerfile, and build the Docker image
# Environment variables: AZURE_DEVOPS_PAT and AZURE_DEVOPS_ORGANIZATION_URL

Push-Location -Path "./mcp-azure-devops"

# Variables
$imageName = "mcp-azure-devops:latest"

# Build the Docker image
docker build -t $imageName .

Write-Host "Docker image '$imageName' built successfully."
Write-Host "To run the container, use:"
Write-Host "  docker run -e AZURE_DEVOPS_PAT=your_token -e AZURE_DEVOPS_ORGANIZATION_URL=your_org_url -p 8000:8000 $imageName"

Pop-Location
