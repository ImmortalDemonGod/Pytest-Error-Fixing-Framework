# branch_fixer/storage/state_manager.py
from typing import Dict, Optional, Set, List, Any, TYPE_CHECKING
from uuid import UUID
from dataclasses import dataclass, field
import time
from uuid import uuid4

if TYPE_CHECKING:
    from src.branch_fixer.storage.session_store import SessionStore
    from src.branch_fixer.orchestration.orchestrator import FixSession, FixSessionState

class StateTransitionError(Exception):
    """Invalid state transition errors"""
    pass

class StateValidationError(Exception):
    """State validation failures"""
    pass

@dataclass
class StateTransition:
    """Records a state transition"""
    from_state: 'FixSessionState'
    to_state: 'FixSessionState'
    timestamp: float
    metadata: Dict[str, Any]
    transition_id: str = field(default_factory=lambda: uuid4().hex[:8])

class StateManager:
    """Manages session state transitions and validation"""
    
    def __init__(self, session_store: Optional['SessionStore'] = None):
        """
        Initialize state manager
        
        Args:
            session_store: Optional store for persistence
        """
        self.session_store = session_store

        # Valid transitions based on state strings
        self.valid_transitions: Dict[str, Set[str]] = {
            'INITIALIZING': {'RUNNING', 'FAILED'},
            'RUNNING': {'PAUSED', 'COMPLETED', 'FAILED', 'ERROR'},
            'PAUSED': {'RUNNING', 'FAILED'},
            'ERROR': {'RUNNING', 'FAILED'},
            'FAILED': set(),      # Terminal state
            'COMPLETED': set()    # Terminal state
        }
        self._transitions: Dict[UUID, List[StateTransition]] = {}

    def validate_transition(self, 
                            from_state: 'FixSessionState',
                            to_state: 'FixSessionState') -> bool:
        """
        Check if state transition is allowed
        
        Args:
            from_state: Current state
            to_state: Desired state
            
        Returns:
            bool indicating if transition is valid
        """
        from_str = from_state.value
        to_str = to_state.value

        if to_str in self.valid_transitions.get(from_str, set()):
            return True
        return False

    def transition_state(self,
                        session: 'FixSession',
                        new_state: 'FixSessionState',
                        metadata: Optional[Dict] = None,
                        force: bool = False) -> bool:
        """
        Execute state transition with validation
        
        Args:
            session: Session to transition
            new_state: Desired new state
            metadata: Additional transition context
            force: Whether to skip validation
            
        Returns:
            bool indicating successful transition
            
        Raises:
            StateTransitionError: If transition invalid
            StateValidationError: If session state invalid
        """
        old_state = session.state

        # If not forcing, validate
        if not force and not self.validate_transition(old_state, new_state):
            raise StateTransitionError(
                f"Invalid transition from {old_state.value} to {new_state.value}"
            )

        # Attempt transition
        session.state = new_state

        # Record transition in memory
        transition_record = StateTransition(
            from_state=old_state,
            to_state=new_state,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self._transitions.setdefault(session.id, []).append(transition_record)

        # Optionally persist the updated session
        if self.session_store:
            self.session_store.save_session(session)

        return True

    def get_transition_history(self, session_id: UUID) -> List[StateTransition]:
        """
        Get complete transition history for session
        
        Args:
            session_id: Session to get history for
            
        Returns:
            List of state transitions in order
        """
        if session_id not in self._transitions:
            return []
        return self._transitions[session_id]

    def validate_session_state(self, session: 'FixSession') -> bool:
        """
        Validate session state is internally consistent
        For example, check if it’s not COMPLETED while errors remain unfixed.

        Returns:
            bool indicating if state is valid
        """
        # Example logic:
        if session.state.value == "COMPLETED":
            # Validate that all errors are done
            if len(session.completed_errors) < len(session.errors):
                raise StateValidationError("Session is marked COMPLETED but not all errors are fixed.")
        return True
