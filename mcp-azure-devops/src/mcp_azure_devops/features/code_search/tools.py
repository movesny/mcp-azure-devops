from dataclasses import dataclass
from typing import List, Optional
from azure.devops.v7_1.git.git_client import GitClient
from azure.devops.v7_1.search.search_client import SearchClient
from azure.devops.v7_1.search.models import CodeSearchRequest
from azure.devops.v7_1.git.models import GitVersionDescriptor
from mcp.server.fastmcp import FastMCP
from mcp_azure_devops.features.code_search.common import get_search_client, get_git_client, AzureDevOpsClientError


@dataclass
class CodeSearchResult:
    repository: str
    file_path: str
    commit: str


def _format_search_results(results: List[CodeSearchResult]) -> str:
    """
    Format the search results into a string representation.
    """
    if not results:
        return "No results found."

    formatted_results = []
    for result in results:
        formatted_results.append(f"Repository: {result.repository}, File: {result.file_path}, Commit: {result.commit}")

    return "\n".join(formatted_results)


def _search_code(
    search_client: SearchClient,
    searchphrase: str,
    project: Optional[str] = None,
    repository: Optional[str] = None,
    branch: Optional[str] = None,
    path: Optional[str] = None,
    skip: Optional[int] = 0,
    top: Optional[int] = 10
) -> List[CodeSearchResult]:
    """
    Search source code via Azure DevOps fulltext index ordered by releavance

    Args:
        search_client: The Azure DevOps SearchClient instance.
        searchphrase: The search phrase to look for in the code. The phrase supports the ADO syntax for "Functional code search" (docs: https://learn.microsoft.com/en-us/azure/devops/project/search/functional-code-search?view=azure-devops#functions-to-find-specific-types-of-code).
        project: The name of the Azure DevOps project.
        repository: The name of the repository to search in (if specified, the project must be specified too).
        branch: The name of the branch to search in (if specified, the repository must be specified too).
        path: The path to search in (if specified, the branch must be specified too).
        skip: The number of results to skip.
        top: The maximum number of results to return.

    Returns:
        List[CodeSearchResult]: A list of search results
    """
    filters = { "Project": [project], "Repository": [repository], "Branch": [branch], "Path": [path] }
    filters = {k: v for k, v in filters.items() if v[0] is not None}
    filters = filters if filters else None

    request = CodeSearchRequest(search_text=searchphrase, filters=filters, skip=skip, top=top)
    search_results = search_client.fetch_code_search_results(request, project)

    results = list()
    for result in search_results.results:
        results.append(CodeSearchResult(
            repository=result.repository.name,
            file_path=result.path,
            commit=result.versions[0].change_id
        ))

    return results


def _download_file_content(
        git_client: GitClient,
        project: str,
        repository: str,
        file_path: str,
        commit: Optional[str] = None
    ) -> str:
        """
        Download the content of a file from Azure DevOps at a specific commit in a repository.
        
        Args:
            git_client: The GitClient instance to use for downloading the file.
            project: The name of the Azure DevOps project.
            repository: The name of the repository.
            file_path: The Unix-style path to the file in the repository.
            commit: The commit ID to download the file from. If not specified, the latest version of the file will be downloaded.

        Returns:
            The content of the file as a string.
        """
        version_descriptor = GitVersionDescriptor(version_type="commit", version=commit) if commit else None
        item = git_client.get_item_content(
            repository_id=repository,
            path=file_path,
            project=project,
            version_descriptor=version_descriptor
        )
        
        # Decode the content, if needed
        file_content = b"".join([chunk for chunk in item])
        decoded_content = file_content.decode('utf-8')

        return decoded_content


def register_tools(mcp: FastMCP) -> None:
    """
    Register pull request tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def search_code(
        searchphrase: str,
        project: Optional[str] = None,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
        path: Optional[str] = None,
        skip: Optional[int] = 0,
        top: Optional[int] = 10
    ) -> str:
        """
        Search source code via Azure DevOps fulltext index ordered by releavance

        Args:
            searchphrase: The search phrase to look for in the code. The phrase supports the ADO syntax for "Functional code search" (docs: https://learn.microsoft.com/en-us/azure/devops/project/search/functional-code-search?view=azure-devops#functions-to-find-specific-types-of-code).
            project: The name of the Azure DevOps project.
            repository: The name of the repository to search in (if specified, the project must be specified too).
            branch: The name of the branch to search in (if specified, the repository must be specified too).
            path: The Unix-style path to search in (if specified, the branch must be specified too). The default is the root of the repository ('/').
            skip: The number of results to skip.
            top: The maximum number of results to return.
        
        Returns:
            Formatted string containing the list of search results
        """
        try:
            search_client = get_search_client()
            search_result = _search_code(
                search_client=search_client,
                project=project,
                repository=repository,
                branch=branch,
                path=path,
                searchphrase=searchphrase,
                skip=skip,
                top=top
            )

            return _format_search_results(search_result)
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"
    

    @mcp.tool()
    def download_file_content(
        project: str,
        repository: str,
        file_path: str,
        commit: Optional[str] = None
    ) -> str:
        """
        Download the content of a file from a specific commit in a repository.
        
        Args:
            project: The name of the Azure DevOps project.
            repository: The name of the repository.
            file_path: The Unix-style path to the file in the repository.
            commit: The commit ID to download the file from. If not specified, the latest version of the file will be downloaded.

        Returns:
            The content of the file as a string.
        """
        git_client = get_git_client()
        content = _download_file_content(
            git_client=git_client,
            project=project,
            repository=repository,
            file_path=file_path,
            commit=commit
        )
        
        return content
