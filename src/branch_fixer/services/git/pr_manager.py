# branch_fixer/services/git/pr_manager.py
import shutil
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from .models import PRDetails, PRStatus, PRChange
from .exceptions import PRUpdateError

logger = logging.getLogger(__name__)


class PRManager:
    """Manages pull request operations with validation and history tracking"""

    def __init__(
        self,
        repository,
        max_files: int = 10,
        required_checks: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the PRManager with a target repository, a per-PR file limit, and required status checks.
        
        Parameters:
        	repository: Repository instance used for creating and tracking pull requests.
        	max_files: Maximum number of files allowed per pull request; must be greater than zero.
        	required_checks: Optional list of required status check names to consider before merging; defaults to an empty list.
        
        Raises:
        	ValueError: If `max_files` is less than or equal to zero.
        """
        if max_files <= 0:
            raise ValueError("max_files must be positive")
        self.repository = repository
        self.max_files = max_files
        self.required_checks = required_checks or []
        self.prs: dict[int, PRDetails] = {}

    def create_pr(
        self,
        title: str,
        description: str,
        branch_name: str,
        modified_files: List[Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PRDetails:
        """
        Create a new pull request record and attempt to create the corresponding PR using the GitHub CLI.
        
        Parameters:
            modified_files (List[Path]): List of modified file paths associated with the PR. Accepted by the method but not used by the current implementation.
            metadata (Optional[Dict[str, Any]]): Additional PR metadata. Accepted by the method but not used by the current implementation.
        
        Returns:
            PRDetails: The created pull request details. The `url` field contains the remote PR URL if the GitHub CLI (`gh`) was available and succeeded in creating the PR; otherwise `url` is `None`.
        """
        pr_id = len(self.prs) + 1
        url: Optional[str] = None

        if shutil.which("gh"):
            try:
                result = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "create",
                        "--title",
                        title,
                        "--body",
                        description,
                        "--head",
                        branch_name,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    url = result.stdout.strip()
                    logger.info(f"Created pull request: {url}")
                else:
                    logger.warning(
                        f"gh pr create failed (exit {result.returncode}): {result.stderr.strip()}"
                    )
            except Exception as exc:
                logger.warning(f"gh pr create raised an exception: {exc}")
        else:
            logger.warning(
                "gh CLI not found — pull request not created. "
                "Install the GitHub CLI (https://cli.github.com) to enable PR creation."
            )

        details = PRDetails(
            id=pr_id,
            title=title,
            description=description,
            branch_name=branch_name,
            status=PRStatus.OPEN,
            created_at=datetime.now(),
            url=url,
        )
        self.prs[pr_id] = details
        return details

    async def update_pr(
        self,
        pr_id: int,
        status: Optional[PRStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> PRDetails:
        """
        Return the stored PRDetails for the given PR identifier without applying any updates.
        
        Optional parameters `status`, `metadata`, and `reason` are accepted for API compatibility but are not used by this implementation.
        
        Args:
            pr_id (int): Identifier of the pull request to retrieve.
            status (Optional[PRStatus]): Ignored.
            metadata (Optional[Dict[str, Any]]): Ignored.
            reason (Optional[str]): Ignored.
        
        Returns:
            PRDetails: The existing pull request details for `pr_id`.
        
        Raises:
            PRUpdateError: If no PR exists with the provided `pr_id`.
        """
        if pr_id not in self.prs:
            raise PRUpdateError("PR not found")
        return self.prs[pr_id]

    async def validate_pr(self, pr_id: int) -> bool:
        """
        Check whether a pull request with the given id is tracked by this manager.
        
        Returns:
            `true` if the PR exists and is tracked, `false` otherwise.
        """
        return pr_id in self.prs

    async def get_pr_history(self, pr_id: int) -> List[PRChange]:
        """
        Retrieve the chronological change history for a pull request.
        
        Parameters:
            pr_id (int): Identifier of the pull request.
        
        Returns:
            List[PRChange]: Changes for the PR ordered from oldest to newest.
        
        Raises:
            NotImplementedError: The operation is not implemented.
        """
        raise NotImplementedError()

    async def close_pr(
        self, pr_id: int, status: PRStatus, reason: Optional[str] = None
    ) -> bool:
        """
        Close the specified pull request and set its final status.
        
        Parameters:
            pr_id (int): Identifier of the pull request to close.
            status (PRStatus): Final status to apply to the PR (e.g., merged or closed).
            reason (Optional[str]): Optional human-readable reason for closing the PR.
        
        Returns:
            True if the pull request was closed, False otherwise.
        
        Raises:
            NotImplementedError: This operation is not implemented.
        """
        raise NotImplementedError()
