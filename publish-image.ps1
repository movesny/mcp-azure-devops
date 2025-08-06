# Set variables
$GHCR_USER = "movesny"
$GHCR_TOKEN = Get-Content -Path "github_token.txt" -Raw
$IMAGE_LOCAL = "mcp-azure-devops:latest"
$IMAGE_REMOTE = "ghcr.io/movesny/mcp-azure-devops:latest"

# Login to GitHub Container Registry
$GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

# Tag image
docker tag $IMAGE_LOCAL $IMAGE_REMOTE

# Push image
docker push $IMAGE_REMOTE
