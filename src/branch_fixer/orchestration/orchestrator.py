# src/branch_fixer/orchestration/orchestrator.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator
from uuid import UUID, uuid4
import logging
import asyncio

from branch_fixer.core.models import TestError, FixAttempt
from branch_fixer.services.ai.manager import AIManager
from branch_fixer.services.pytest.runner import TestRunner
from branch_fixer.services.code.change_applier import ChangeApplier
from branch_fixer.services.git.repository import GitRepository

logger = logging.getLogger(__name__)

class FixSessionState(Enum):
    """Possible states for a fix session"""
    INITIALIZING = "initializing"
    RUNNING = "running" 
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    ERROR = "error"



@dataclass
class FixProgress:
    """Tracks progress of fix operations"""
    total_errors: int
    fixed_count: int
    current_error: Optional[str]
    retry_count: int
    current_temperature: float
    last_error: Optional[str] = None

@dataclass
class FixSession:
    """Tracks state for a test fixing session"""
    id: UUID = field(default_factory=uuid4)
    state: FixSessionState = FixSessionState.INITIALIZING
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[TestError] = field(default_factory=list)
    completed_errors: List[TestError] = field(default_factory=list) 
    current_error: Optional[TestError] = None
    retry_count: int = 0
    error_count: int = 0
    modified_files: List[Path] = field(default_factory=list)
    git_branch: Optional[str] = None

    def create_snapshot(self) -> Dict[str, Any]:
        """Create serializable snapshot of current state"""
        raise NotImplementedError()

class FixOrchestrator:
    """Orchestrates test fixing workflow with state management and error handling"""
    
    def __init__(self,
                 ai_manager: AIManager,
                 test_runner: TestRunner, 
                 change_applier: ChangeApplier,
                 git_repo: GitRepository,
                 *,
                 max_retries: int = 3,
                 initial_temp: float = 0.4,
                 temp_increment: float = 0.1,
                 interactive: bool = True):
        """Initialize orchestrator with required components and settings
        
        Args:
            ai_manager: AI service for generating fixes
            test_runner: Test execution service
            change_applier: Code change service
            git_repo: Git operations service
            max_retries: Maximum fix attempts per error
            initial_temp: Initial temperature for AI
            temp_increment: Temperature increase per retry
            interactive: Whether to enable interactive mode
            
        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If component initialization fails
        """
        raise NotImplementedError()

    async def start_session(self, errors: List[TestError]) -> FixSession:
        """Start a new fix session
        
        Args:
            errors: List of errors to fix
            
        Returns:
            New FixSession instance
            
        Raises:
            SessionError: If session creation fails
            ValueError: If errors list is empty
        """
        raise NotImplementedError()

    async def run_session(self, session_id: UUID) -> bool:
        """Run an existing fix session
        
        Args:
            session_id: ID of session to run
            
        Returns:
            bool indicating if all errors were fixed
            
        Raises:
            SessionError: If session not found or execution fails
            RuntimeError: If session is in invalid state
        """
        raise NotImplementedError()

    async def fix_error(self, error: TestError) -> bool:
        """Attempt to fix a single test error
        
        Args:
            error: TestError to fix
            
        Returns:
            bool indicating if fix succeeded
            
        Raises:
            FixAttemptError: If fix attempt fails
            ValueError: If error is invalid
            RuntimeError: If no active session
        """
        raise NotImplementedError()

    async def get_progress(self) -> AsyncIterator[FixProgress]:
        """Stream progress updates for current session
        
        Yields:
            FixProgress objects with current status
            
        Raises:
            RuntimeError: If no active session
        """
        raise NotImplementedError()

    def pause_session(self) -> bool:
        """Pause current fix session
        
        Returns:
            bool indicating if pause succeeded
            
        Raises:
            RuntimeError: If no active session
            SessionError: If pause fails
        """
        raise NotImplementedError()

    async def resume_session(self) -> bool:
        """Resume paused fix session
        
        Returns:
            bool indicating if resume succeeded
            
        Raises:
            RuntimeError: If no active session
            SessionError: If session not paused or resume fails
        """
        raise NotImplementedError()

    async def handle_error(self, error: Exception) -> bool:
        """Handle errors during fix process
        
        Args:
            error: Exception that occurred
            
        Returns:
            bool indicating if error was handled
            
        Raises:
            RuntimeError: If no active session
        """
        raise NotImplementedError()
