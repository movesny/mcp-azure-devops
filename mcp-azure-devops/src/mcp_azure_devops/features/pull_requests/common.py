from azure.devops.v7_1.git.git_client import GitClient
from azure.devops.v7_1.policy.policy_client import PolicyClient
from azure.devops.v7_1.identity.identity_client import IdentityClient
from mcp_azure_devops.utils.azure_client import get_connection


class AzureDevOpsClientError(Exception):
    """Exception raised for errors in Azure DevOps client operations."""
    pass


def get_git_client() -> GitClient:
    """
    Get the git client for Azure DevOps.
    
    Returns:
        GitClient instance
        
    Raises:
        AzureDevOpsClientError: If connection or client creation fails
    """
    # Get connection to Azure DevOps
    connection = get_connection()
    
    if not connection:
        raise AzureDevOpsClientError(
            "Azure DevOps PAT or organization URL not found in "
            "environment variables."
        )
    
    # Get the git client
    git_client = connection.clients_v7_1.get_git_client()
    
    if git_client is None:
        raise AzureDevOpsClientError("Failed to get git client.")
    
    return git_client


def get_identity_client() -> IdentityClient:
    """
    Get the identity client using the same Azure DevOps connection.
    IMPORTANT: The PAT must be set to global access and not just to one org,
               otherwise we the identity client will be returning 401 HTTP errors.
    
    Returns:
        IdentityClient instance
        
    Raises:
        AzureDevOpsClientError: If connection or client creation fails
    """
    # Get connection to Azure DevOps
    connection = get_connection()
    
    if not connection:
        raise AzureDevOpsClientError(
            "Azure DevOps PAT or organization URL not found in "
            "environment variables."
        )
    
    # Get the clients
    identity_client = connection.clients_v7_1.get_identity_client()
    
    if identity_client is None:
        raise AzureDevOpsClientError("Failed to get identity client.")
    
    return identity_client


def get_policy_client() -> PolicyClient:
    """
    Get the policy client for Azure DevOps.
    
    Returns:
        PolicyClient instance

    Raises:
        AzureDevOpsClientError: If connection or client creation fails
    """
    # Get connection to Azure DevOps
    connection = get_connection()
    
    if not connection:
        raise AzureDevOpsClientError(
            "Azure DevOps PAT or organization URL not found in "
            "environment variables."
        )

    # Get the policy client
    policy_client = connection.clients_v7_1.get_policy_client()

    if policy_client is None:
        raise AzureDevOpsClientError("Failed to get policy client.")

    return policy_client
