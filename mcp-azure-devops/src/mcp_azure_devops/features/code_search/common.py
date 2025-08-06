from azure.devops.v7_1.git.git_client import GitClient
from azure.devops.v7_1.search.search_client import SearchClient
from mcp_azure_devops.utils.azure_client import get_connection


class AzureDevOpsClientError(Exception):
    """Exception raised for errors in Azure DevOps client operations."""
    pass


def get_search_client() -> SearchClient:
    """
    Get the search client for Azure DevOps.
    
    Returns:
        SearchClient instance
        
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

    # Get the search client
    search_client = connection.clients_v7_1.get_search_client()

    if search_client is None:
        raise AzureDevOpsClientError("Failed to get search client.")

    return search_client

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
