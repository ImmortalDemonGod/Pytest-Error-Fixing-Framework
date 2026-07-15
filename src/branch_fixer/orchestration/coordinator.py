# branch_fixer/orchestration/coordinator.py
from typing import Dict, Any
from uuid import UUID


class CoordinationError(Exception):
    """Base exception for coordination errors"""

    pass


class SessionCoordinator:
    """Manages state transitions and coordinates component interactions"""

    def __init__(self):
        """Initialize session coordinator"""
        self.sessions: Dict[UUID, Any] = {}
