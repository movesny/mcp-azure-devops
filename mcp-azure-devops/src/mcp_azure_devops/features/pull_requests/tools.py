import re
from typing import Optional, List
from azure.devops.v7_1.git.git_client import GitClient
from azure.devops.v7_1.identity.identity_client import IdentityClient
from azure.devops.v7_1.git.models import GitPullRequest, GitPullRequestSearchCriteria, GitPullRequestCommentThread, ResourceRef, IdentityRefWithVote, GitPullRequestCompletionOptions, Comment
from mcp.server.fastmcp import FastMCP
from mcp_azure_devops.features.pull_requests.common import get_git_client, get_identity_client, AzureDevOpsClientError


def _format_pull_request(pull_request: GitPullRequest) -> str:
    """
    Format pull request information.

    Args:
        pull_request: PullRequest object to format
        
    Returns:
        String with pull request details
    """
    # Basic information that should always be available
    formatted_info = [f"# Pull request: {pull_request.title}"]
    formatted_info.append(f"ID: {pull_request.pull_request_id}")
    formatted_info.append(f"Is Draft: {pull_request.is_draft}")
    formatted_info.append(f"Source Ref Name: {pull_request.source_ref_name}")
    formatted_info.append(f"Target Ref Name: {pull_request.target_ref_name}")

    # Add status and merge status if available
    if hasattr(pull_request, "status") and pull_request.status:
        formatted_info.append(f"Status: {pull_request.status}")
    if hasattr(pull_request, "merge_status") and pull_request.merge_status:
        formatted_info.append(f"Merge Status: {pull_request.merge_status}")

    # Azure DevOps PR reviewer vote meanings:
    vote_map = {
        10: 'approved',
        5: 'approved with suggestions',
        0: 'no vote',
        -5: 'waiting for author',
        -10: 'rejected'
    }

    # Add reviewers and their votes if available
    if hasattr(pull_request, "reviewers") and pull_request.reviewers:
        reviewer_lines = []
        for reviewer in pull_request.reviewers:
            vote = getattr(reviewer, 'vote', 0)
            display_name = getattr(reviewer, 'display_name', '')
            is_required = getattr(reviewer, 'is_required', 'False')
            vote_str = vote_map.get(vote, f'unknown ({vote})')
            reviewer_lines.append(f"Reviewer: {display_name}, Is Required: {is_required}, Vote: {vote_str}")
        formatted_info.append("Reviewers:")
        formatted_info.extend([f"- {line}" for line in reviewer_lines])
    
    # Add work items references if available
    if (hasattr(pull_request, "work_item_refs") and pull_request.work_item_refs):
        formatted_info.append("Linked Work Items:")
        for work_item in pull_request.work_item_refs:
            formatted_info.append(_format_work_item_ref(work_item))

    # Add description if available
    if hasattr(pull_request, "description") and pull_request.description:
        formatted_info.append(f"Description: {pull_request.description}")

    return "\n".join(formatted_info)


def _format_thread(thread: GitPullRequestCommentThread) -> str:
    """
    Format thread information.

    Args:
        thread: Thread object to format
        
    Returns:
        String with thread details
    """
    # Basic information that should always be available
    formatted_info = [f"# Thread ID: {thread.id}"]

    # Add status if available
    if hasattr(thread, "status") and thread.status:
        formatted_info.append(f"Status: {thread.status}")
    if hasattr(thread, "is_deleted") and thread.is_deleted:
        formatted_info.append(f"Is Deleted: {thread.is_deleted}")
    
    # Add context if available
    if hasattr(thread, "thread_context") and thread.thread_context:
        lines = ""
        if hasattr(thread.thread_context, "right_file_start") and hasattr(thread.thread_context, "right_file_end"):
            if thread.thread_context.right_file_start.line == thread.thread_context.right_file_end.line:
                lines = f" (line: {thread.thread_context.right_file_start.line})"
            else:
                lines = f" (lines: {thread.thread_context.right_file_start.line}-{thread.thread_context.right_file_end.line})"
        formatted_info.append(f"Thread Context: {thread.thread_context.file_path}{lines}")

    # Add comments if available
    if hasattr(thread, "comments") and thread.comments:
        formatted_info.append("Comments:")
        for comment in thread.comments:
            formatted_info.append(f"- [{comment.author.display_name}] {comment.content}")
    
    return "\n".join(formatted_info)


def _format_work_item_ref(work_item_ref: ResourceRef) -> str:
    """
    Format work item reference information.

    Args:
        work_item_ref: Work item reference object to format
        
    Returns:
        String with work item reference details
    """
    return f"- ID: {work_item_ref.id} (URL: {work_item_ref.url})"


def _get_pull_requests_impl(
    git_client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    search_criteria: Optional[GitPullRequestSearchCriteria] = None,
    skip: Optional[int] = None,
    top: Optional[int] = None
) -> str:
    """
    Implementation of pull requests retrieval.
    
    Args:
        git_client: Git client
        project_id_or_name: Azure DevOps project ID or name
        repository_id: Azure DevOps repository ID or name
        search_critaria: Filter by the curiteria (optional).
        skip: Skip fist N items (optional)
        top: List only first M items (optional)
    
    Returns:
        Formatted string containing pull request information
    """
    try:
        pull_requests = git_client.get_pull_requests(
                repository_id=repository_id,
                project=project_id_or_name,
                search_criteria=search_criteria,
                skip=skip,
                top=top,
            )
        
        if not pull_requests:
            return "No pull requests found."
        
        formatted_prs = []
        for pr in pull_requests:
            formatted_prs.append(_format_pull_request(pr))
        
        return "\n\n".join(formatted_prs)
            
    except Exception as e:
        return f"Error retrieving pull requests: {str(e)}"


def _get_pull_request_impl(
    git_client: GitClient,
    repository_id: str,
    id: int,
    project_id_or_name: Optional[str] = None,
    include_work_item_refs: Optional[bool] = True
) -> str:
    """
    Implementation of pull request retrieval.
    
    Args:
        git_client: Git client
        repository_id: Azure DevOps repository ID or name
        id: ID of the Pull Request
        project_id_or_name: Azure DevOps project ID or name (must be filled if the repository is referenced by name and not by ID)
        include_work_item_refs: Whether to include work item references in the response (optional)
    
    Returns:
        Formatted string containing pull request information
    """
    try:
        pull_request = git_client.get_pull_request(
            repository_id=repository_id,
            pull_request_id=id,
            project=project_id_or_name,
            include_work_item_refs=include_work_item_refs,
        )
        
        if not pull_request:
            return "Pull request not found."
        
        formated_pr = _format_pull_request(pull_request)
        return formated_pr
            
    except Exception as e:
        return f"Error retrieving pull request ID {id}: {str(e)}"


def _get_pr_threads_impl(
    git_client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
) -> str:
    """
    Implementation of PR threads retrieval.
    
    Args:
        git_client: Git client
        project_id_or_name: Azure DevOps project ID or name
        repository_id: Azure DevOps repository ID or name
        pull_request_id: ID of the Pull Request
    
    Returns:
        Formatted string containing threads and comments information
    """
    try:
        threads = git_client.get_threads(
            project=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
        )
        
        if not threads:
            return "No PR threads found."
        
        formatted_threads = []
        for thread in threads:
            formatted_threads.append(_format_thread(thread))
        
        return "\n\n".join(formatted_threads)
            
    except Exception as e:
        return f"Error retrieving threads: {str(e)}"


def _get_pr_work_items_impl(
    git_client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
) -> str:
    """
    Implementation of PR work items retrieval.

    Args:
        git_client: Git client
        project_id_or_name: Azure DevOps project ID or name
        repository_id: Azure DevOps repository ID or name
        pull_request_id: ID of the Pull Request
    
    Returns:
        Formatted string containing linked work items information
    """
    try:
        work_items = git_client.get_pull_request_work_item_refs(
            project=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
        )
        
        if not work_items:
            return "No PR work items found."

        formatted_work_items = [f"Linked Work Items for PR ID {pull_request_id}:"]
        for work_item in work_items:
            formatted_work_items.append(_format_work_item_ref(work_item))

        return "\n".join(formatted_work_items)

    except Exception as e:
        return f"Error retrieving work items: {str(e)}"


def _is_guid(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", s))


def _is_email(s: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))


def _resolve_reviewer_guid(identity_client: IdentityClient, reviewer: str) -> str:
    if _is_guid(reviewer):
        return reviewer
    
    try:
        if _is_email(reviewer):
            identities = identity_client.read_identities(search_filter="MailAddress", filter_value=reviewer)
        else:
            identities = identity_client.read_identities(search_filter="DisplayName", filter_value=reviewer)
        
        if identities and len(identities) > 0:
            return identities[0].id
        else:
            raise Exception(f"Could not resolve reviewer '{reviewer}' to a GUID.")
    except Exception as e:
        raise Exception(f"Failed to resolve reviewer '{reviewer}': {str(e)}")


def _create_pull_request_impl(
    git_client: GitClient,
    identity_client: IdentityClient,
    project_id_or_name: str,
    repository_id: str,
    title: str,
    description: str,
    source_branch: str,
    target_branch: str,
    required_reviewers: Optional[List[str]] = None,
    optional_reviewers: Optional[List[str]] = None,
    is_draft: Optional[bool] = False
) -> str:
    """
    Implementation of pull request creation.
    
    Args:
        git_client: Git client
        identity_client: Identity client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        title: PR title
        description: PR description
        source_branch: Source branch name
        target_branch: Target branch name
        required_reviewers: List of required reviewer names or emails or GUIDs (optional)
        optional_reviewers: List of optional reviewer names or emails or GUIDs (optional)
        is_draft: Whether the PR is a draft (optional, default False)
    
    Returns:
        Formatted string containing pull request information
    """
    try:
        resolved_reviewers = []
        if optional_reviewers:
            for reviewer in optional_reviewers:
                guid = _resolve_reviewer_guid(identity_client, reviewer)
                resolved_reviewers.append(IdentityRefWithVote(id=guid, is_required=False))

        if required_reviewers:
            for reviewer in required_reviewers:
                guid = _resolve_reviewer_guid(identity_client, reviewer)
                resolved_reviewers.append(IdentityRefWithVote(id=guid, is_required=True))
        
        pr = GitPullRequest(
            title=title,
            description=description,
            source_ref_name=f"refs/heads/{source_branch}",
            target_ref_name=f"refs/heads/{target_branch}",
            is_draft=is_draft,
            reviewers=resolved_reviewers
        )

        result = git_client.create_pull_request(
            git_pull_request_to_create=pr,
            project=project_id_or_name,
            repository_id=repository_id
        )
        
        return _format_pull_request(result)
    except Exception as e:
        return f"Error creating pull request: {str(e)}"


def _update_pull_request_core_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    completion_options: Optional[GitPullRequestCompletionOptions] = None
) -> GitPullRequest:
    """
    Implementation of pull request update.
    
    Args:
        client: Git client
        pull_request_id: ID of the PR to update
        title: New PR title (optional)
        description: New PR description (optional)
        status: New PR status (optional)
    
    Returns:
        Formatted string containing updated pull request information
    """
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if completion_options is not None:
        update_data["completion_options"] = completion_options
    if status is not None:
        update_data["status"] = status
        if status == "completed":
            # Last merge source commit is required for some completion options
            existing_pull_request = client.get_pull_request(
                project=project_id_or_name,
                repository_id=repository_id,
                pull_request_id=pull_request_id
            )
            update_data["last_merge_source_commit"] = existing_pull_request.last_merge_source_commit
    
    if not update_data:
        raise Exception ("Error: No update parameters provided")
    
    pull_request = GitPullRequest()
    for key, value in update_data.items():
        setattr(pull_request, key, value)
    
    result = client.update_pull_request(
        project=project_id_or_name,
        repository_id=repository_id,
        pull_request_id=pull_request_id,
        git_pull_request_to_update=pull_request,
    )
    
    return result


def _update_pull_request_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Implementation of pull request update.
    
    Args:
        client: Git client
        pull_request_id: ID of the PR to update
        title: New PR title (optional)
        description: New PR description (optional)
        status: New PR status (optional)
    
    Returns:
        Formatted string containing updated pull request information
    """
    try:
        result = _update_pull_request_core_impl(
            client=client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            title=title,
            description=description,
        )
        
        return _format_pull_request(result)
    except Exception as e:
        return f"Error updating pull request: {str(e)}"


def _add_comment_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    content: str,
    comment_thread_id: Optional[int] = None,
    parent_comment_id: Optional[int] = None
) -> str:
    """
    Implementation of comment addition.
    
    Args:
        client: Git client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
        content: Comment text
        comment_thread_id: ID of existing thread (for replies)
        parent_comment_id: ID of parent comment (for replies)
    
    Returns:
        Formatted string containing comment information
    """
    try:
        if comment_thread_id:
            # Add comment to existing thread
            comment = Comment(content=content)
            if parent_comment_id:
                comment.parent_comment_id = parent_comment_id
            
            result = client.create_comment(
                comment=comment,
                repository_id=repository_id,
                pull_request_id=pull_request_id,
                thread_id=comment_thread_id,
                project=project_id_or_name
            )

            return f"Comment ID {result.id} added successfully to the thread"
        else:
            # Create new thread with comment
            comment = Comment(content=content)
            thread = GitPullRequestCommentThread(comments=[comment], status="active")

            result = client.create_thread(
                comment_thread=thread,
                repository_id=repository_id,
                pull_request_id=pull_request_id,
                project=project_id_or_name
            )

            return f"Comment added successfully to thread ID: {result.id}"
        
    except Exception as e:
        return f"Error adding comment: {str(e)}"


def _update_thread_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    comment_thread_id: int,
    state: str,
) -> str:
    """
    Implementation of comment thread resolving.
    
    Args:
        client: Git client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
        comment_thread_id: ID of existing thread (for replies)
        state: status to set for the thread
    
    Returns:
        Formatted string containing thread state information
    """
    try:
        thread = GitPullRequestCommentThread(status=state)
        
        result = client.update_thread(
            comment_thread=thread,
            project=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            thread_id=comment_thread_id)

        return f"Thread ID {result.id} successfully changed state to {result.status}"
    except Exception as e:
        return f"Error updating state of the thread ID {comment_thread_id}: {str(e)}"


def _complete_pull_request_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    merge_strategy: Optional[str] = "squash",
    delete_source_branch: Optional[bool] = False
) -> str:
    """
    Implementation of pull request completion.
    
    Args:
        client: Azure DevOps client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
        merge_strategy: Strategy to use (squash, rebase, rebaseMerge, merge)
        delete_source_branch: Whether to delete source branch after merge
    
    Returns:
        Formatted string containing completion information
    """
    try:
        result = _update_pull_request_core_impl(
            client=client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            status="completed",
            completion_options = GitPullRequestCompletionOptions(
                merge_strategy=merge_strategy,
                delete_source_branch=delete_source_branch
            )
        )
        
        completed_by = result.closed_by.display_name if result.closed_by else 'Unknown'
        return f"Pull request {pull_request_id} completed successfully by {completed_by}\nMerge strategy: {merge_strategy}\nSource branch deleted: {delete_source_branch}"
    except Exception as e:
        return f"Error completing pull request: {str(e)}"


def _abandon_pull_request_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int
) -> str:
    """
    Implementation of abandoning a pull request.
    
    Args:
        client: Azure DevOps client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
    
    Returns:
        Formatted string containing PR state change information
    """
    try:
        result = _update_pull_request_core_impl(
            client=client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            status="abandoned"
        )
        
        return f"Successfully abandoned pull request #{pull_request_id}."
    except Exception as e:
        return f"Failed to abandon pull request #{pull_request_id}."


def _reactivate_pull_request_impl(
    client: GitClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int
) -> str:
    """
    Implementation of pull request reactivation.
    
    Args:
        client: Azure DevOps client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
    
    Returns:
        Formatted string containing PR state change information
    """
    try:
        result = _update_pull_request_core_impl(
            client=client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            status="active"
        )
        
        return f"Successfully reactivated pull request #{pull_request_id}."
    except Exception as e:
        return f"Failed to reactivate pull request #{pull_request_id}: {str(e)}."


def _set_vote_core_impl(
    git_client: GitClient,
    identity_client: IdentityClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int,
    vote: int) -> IdentityRefWithVote:
    """
    Implementation of pull request voting.
    
    Args:
        git_client: Git client
        identity_client: Identity client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
        vote: Vote value (10=approve, 5=approve with suggestions, 0=no vote, -5=wait for author, -10=reject)
    
    Returns:
        Updated reviewer details
    """
    try:
        self_identity = identity_client.get_self()
        reviewer_id = self_identity.id
        reviewer = IdentityRefWithVote(id=reviewer_id, vote=vote)
        
        result = git_client.create_pull_request_reviewer(
            reviewer=reviewer,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            reviewer_id=reviewer_id,
            project=project_id_or_name
        )
        
        return result
    except Exception as e:
        raise AzureDevOpsClientError(f"Failed to set vote: {str(e)}")


def _approve_pull_request_impl(
    git_client: GitClient,
    identity_client: IdentityClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int
) -> str:
    """
    Implementation of pull request approval.
    
    Args:
        git_client: Git client
        identity_client: Identity client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
    
    Returns:
        Formatted string containing approval information
    """
    try:
        result = _set_vote_core_impl(
            git_client=git_client,
            identity_client=identity_client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            vote=10  # 10 = Approve
        )
        
        return f"Pull request {pull_request_id} approved by {result.display_name}"
    except Exception as e:
        return f"Error approving pull request: {str(e)}"


def _reject_pull_request_impl(
    git_client: GitClient,
    identity_client: IdentityClient,
    project_id_or_name: str,
    repository_id: str,
    pull_request_id: int
) -> str:
    """
    Implementation of pull request rejection.
    
    Args:
        git_client: Git client
        identity_client: Identity client
        project_id_or_name: Project ID or name
        repository_id: Repository ID or name
        pull_request_id: ID of the PR
    
    Returns:
        Formatted string containing rejection information
    """
    try:
        result = _set_vote_core_impl(
            git_client=git_client,
            identity_client=identity_client,
            project_id_or_name=project_id_or_name,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            vote=-10  # -10 = Reject
        )
        
        return f"Pull request {pull_request_id} rejected by {result.display_name}"
    except Exception as e:
        return f"Error rejecting pull request: {str(e)}"



def register_tools(mcp: FastMCP) -> None:
    """
    Register pull request tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def get_pull_requests(
        project: str,
        repository: str,
        status: Optional[str] = None,
        creator: Optional[str] = None,
        reviewer: Optional[str] = None,
        target_branch: Optional[str] = None,
    ) -> str:
        """
        Retrieves all pull requests in the Azure DevOps project.

        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            status: Filter by status (active, abandoned, completed, all) (optional). Defaults to 'active'.
            creator: Filter by creator ID (optional)
            reviewer: Filter by reviewer ID (optional)
            target_branch: Filter by target branch name (optional)
        
        Returns:
            Formatted string containing pull request information
        """
        try:
            search_criteria = GitPullRequestSearchCriteria(
                status=status,
                creator_id=creator,
                reviewer_id=reviewer,
                target_ref_name=target_branch)
            
            git_client = get_git_client()
            return _get_pull_requests_impl(
                git_client,
                project,
                repository,
                search_criteria
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def get_pull_request(
        project: str,
        repository: str,
        pull_request_id: int,
    ) -> str:
        """
        Retrieves a pull request by ID from the Azure DevOps. The response includes Work Item references, if there are any.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the Pull Request
        
        Returns:
            Formatted string containing pull request information
        """
        try:
            git_client = get_git_client()
            return _get_pull_request_impl(
                git_client,
                repository,
                pull_request_id,
                project_id_or_name=project,
                include_work_item_refs=True
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def get_pr_threads(
        project: str,
        repository: str,
        pull_request_id: int,
    ) -> str:
        """
        Get all threads and all the comments in a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the Pull Request
        
        Returns:
            Formatted string containing threads and comments information
        """
        try:
            git_client = get_git_client()
            return _get_pr_threads_impl(
                git_client,
                project,
                repository,
                pull_request_id,
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def get_pr_work_items(
        project: str,
        repository: str,
        pull_request_id: int,
    ) -> str:
        """
        Get work items linked to a Pull Request in Azure DevOps project.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name            
            pull_request_id: ID of the Pull Request
        
        Returns:
            Formatted string containing linked work items information
        """
        try:
            git_client = get_git_client()
            return _get_pr_work_items_impl(
                git_client,
                project,
                repository,
                pull_request_id,
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"
        
    
    @mcp.tool()
    def create_pull_request(
        project: str,
        repository: str,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        required_reviewers: Optional[List[str]] = None,
        optional_reviewers: Optional[List[str]] = None,
        is_draft: Optional[bool] = False,
    ) -> str:
        """
        Create a new Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            title: PR title
            description: PR description
            source_branch: Source branch name
            target_branch: Target branch name
            required_reviewers: List of required reviewers (optional, default None)
            optional_reviewers: List of optional reviewers (optional, default None)
            is_draft: Whether the PR is a draft (optional, default False)
        
        Returns:
            Formatted string containing pull request information
        """
        try:
            git_client = get_git_client()
            identity_client = get_identity_client()
            return _create_pull_request_impl(
                git_client=git_client,
                identity_client=identity_client,
                project_id_or_name=project,
                repository_id=repository,
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                optional_reviewers=optional_reviewers,
                required_reviewers=required_reviewers,
                is_draft=is_draft)
        
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def update_pull_request(
        project: str,
        repository: str,
        pull_request_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Update an existing Pull Request in Azure DevOps.
        
        Args:
            organization: Azure DevOps organization name
            project: Azure DevOps project name
            repo: Azure DevOps repository name
            pull_request_id: ID of the PR to update
            title: New PR title (optional)
            description: New PR description (optional)
        
        Returns:
            Formatted string containing updated pull request information
        """
        try:
            client = get_git_client()
            return _update_pull_request_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id,
                title=title,
                description=description
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def add_comment(
        project: str,
        repository: str,
        pull_request_id: int,
        content: str,
        comment_thread_id: Optional[int] = None,
        parent_comment_id: Optional[int] = None
    ) -> str:
        """
        Add a comment to a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
            content: Comment text
            comment_thread_id: ID of existing thread (for replies)
            parent_comment_id: ID of parent comment (for replies)
        
        Returns:
            Formatted string containing comment information
        """
        try:
            client = get_git_client()
            return _add_comment_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id,
                content=content,
                comment_thread_id=comment_thread_id,
                parent_comment_id=parent_comment_id)
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def resolve_thread(
        project: str,
        repository: str,
        pull_request_id: int,
        comment_thread_id: int
    ) -> str:
        """
        Resolve a comment thread in Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
            comment_thread_id: ID of existing thread
        
        Returns:
            Formatted string containing thread status information
        """
        try:
            client = get_git_client()
            return _update_thread_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id,
                comment_thread_id=comment_thread_id,
                state="fixed")
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def reactivate_thread(
        project: str,
        repository: str,
        pull_request_id: int,
        comment_thread_id: int
    ) -> str:
        """
        Reactivate a resolved comment thread in Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
            comment_thread_id: ID of existing thread
        
        Returns:
            Formatted string containing thread status information
        """
        try:
            client = get_git_client()
            return _update_thread_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id,
                comment_thread_id=comment_thread_id,
                state="active")
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def approve_pull_request(
        project: str,
        repository: str,        
        pull_request_id: int
    ) -> str:
        """
        Approve a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
        
        Returns:
            Formatted string containing approval information
        """
        try:
            git_client = get_git_client()
            identity_client = get_identity_client()
            return _approve_pull_request_impl(
                git_client=git_client,
                identity_client=identity_client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def reject_pull_request(
        project: str,
        repository: str,
        pull_request_id: int
    ) -> str:
        """
        Reject a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
        
        Returns:
            Formatted string containing rejection information
        """
        try:
            git_client = get_git_client()
            identity_client = get_identity_client()
            return _reject_pull_request_impl(
                git_client=git_client,
                identity_client=identity_client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def complete_pull_request(
        project: str,
        repository: str,
        pull_request_id: int,
        merge_strategy: Optional[str] = "squash",
        delete_source_branch: Optional[bool] = True
    ) -> str:
        """
        Complete (merge) a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
            merge_strategy: Merge strategy (squash, rebase, rebaseMerge, merge) (optional)
            delete_source_branch: Whether to delete source branch after merge (optional)
        
        Returns:
            Formatted string containing completion information
        """
        try:
            client = get_git_client()
            return _complete_pull_request_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id,
                merge_strategy=merge_strategy,
                delete_source_branch=delete_source_branch
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def abandon_pull_request(
        project: str,
        repository: str,
        pull_request_id: int
    ) -> str:
        """
        Abandon a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
        
        Returns:
            Formatted string containing PR state change information
        """
        try:
            client = get_git_client()
            return _abandon_pull_request_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


    @mcp.tool()
    def reactivate_pull_request(
        project: str,
        repository: str,
        pull_request_id: int
    ) -> str:
        """
        Reactivate a Pull Request in Azure DevOps.
        
        Args:
            project: Azure DevOps project name
            repository: Azure DevOps repository name
            pull_request_id: ID of the PR
        
        Returns:
            Formatted string containing PR state change information
        """
        try:
            client = get_git_client()
            return _reactivate_pull_request_impl(
                client=client,
                project_id_or_name=project,
                repository_id=repository,
                pull_request_id=pull_request_id
            )
        except AzureDevOpsClientError as e:
            return f"Error: {str(e)}"


#
# Below I was trying to figure out the policy evaluations like the build, expiratinon checks, etc.
#
# # Note that this thing simply does not work, because the evaluation
# # is failing with a message that it does not exist or I don't have permissions to view it.
# # I tried this with different PRs and full acess PAT and it still did not work.
# pull_request_id=252800
# project_id_or_name=ADO_PROJECT

# git_client = get_git_client()
# # making this into a tool could be useful; although, there is maybe a better method,
# # which can include also work item refs within a single request
# pr = git_client.get_pull_request_by_id(
#     project=project_id_or_name,
#     pull_request_id=pull_request_id
# )

# # Get policy evaluations
# policy_client = get_policy_client()
# evaluations = policy_client.get_policy_evaluations(
#     project=project_id_or_name,
#     artifact_id=pr.artifact_id
# )

# for evaluation in evaluations:
#     print(f"Policy Evaluation ID: {evaluation.id}")
#     print(f"Policy Type: {evaluation.policy_type}")
#     print(f"Status: {evaluation.status}")
#     print(f"Created Date: {evaluation.created_date}")
#     print(f"Last Updated Date: {evaluation.last_updated_date}")
#     print(f"Configuration: {evaluation.configuration}")
