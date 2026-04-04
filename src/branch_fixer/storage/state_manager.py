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

    from_state: "FixSessionState"
    to_state: "FixSessionState"
    timestamp: float
    metadata: Dict[str, Any]
    transition_id: str = field(default_factory=lambda: uuid4().hex[:8])


class StateManager:
    """Manages session state transitions and validation"""

    def __init__(self, session_store: Optional["SessionStore"] = None):
        """
        Create a StateManager and configure allowed session-state transitions.
        
        Stores the optional session_store used for persistence, initializes the mapping of allowed state-to-state transitions (by lowercase state string), and prepares an empty in-memory transition history dictionary.
        
        Parameters:
            session_store (Optional[SessionStore]): Optional persistence backend used to save session updates.
        """
        self.session_store = session_store

        # Valid transitions based on state strings
        self.valid_transitions: Dict[str, Set[str]] = {
            "initializing": {"running", "failed"},
            "running": {"paused", "completed", "failed", "error"},
            "paused": {"running", "failed"},
            "error": {"running", "failed"},
            "failed": set(),  # Terminal state
            "completed": set(),  # Terminal state
        }
        self._transitions: Dict[UUID, List[StateTransition]] = {}

    def validate_transition(
        self, from_state: "FixSessionState", to_state: "FixSessionState"
    ) -> bool:
        """
        Determine whether a transition from one FixSessionState to another is permitted.
        
        Args:
            from_state (FixSessionState): The current session state.
            to_state (FixSessionState): The desired session state.
        
        Returns:
            `true` if the transition is allowed, `false` otherwise.
        """
        from_str = from_state.value
        to_str = to_state.value

        if to_str in self.valid_transitions.get(from_str, set()):
            return True
        return False

    def transition_state(
        self,
        session: "FixSession",
        new_state: "FixSessionState",
        metadata: Optional[Dict] = None,
        force: bool = False,
    ) -> bool:
        """
        Transition a FixSession to a new state, record the transition, and optionally persist the updated session.
        
        Parameters:
            session (FixSession): The session to update.
            new_state (FixSessionState): The target state for the session.
            metadata (Optional[Dict]): Additional context to record with the transition.
            force (bool): If true, skip validation of whether the transition is allowed.
        
        Returns:
            True if the transition was recorded (and persisted when a session store is configured).
        
        Raises:
            StateTransitionError: If the transition is not allowed and `force` is False.
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
            metadata=metadata or {},
        )
        self._transitions.setdefault(session.id, []).append(transition_record)

        # Optionally persist the updated session
        if self.session_store:
            self.session_store.save_session(session)

        return True

    def get_transition_history(self, session_id: UUID) -> List[StateTransition]:
        """
        Retrieve the recorded state transition history for a session.
        
        Parameters:
            session_id (UUID): Identifier of the session whose history to retrieve.
        
        Returns:
            List[StateTransition]: Ordered list of recorded state transitions for the session; empty list if no history exists.
        """
        if session_id not in self._transitions:
            return []
        return self._transitions[session_id]

    def validate_session_state(self, session: "FixSession") -> bool:
        """
        Validate that a session's state is internally consistent.
        
        If the session is in the "completed" state, ensures the number of completed errors equals the total number of errors; if fewer completed errors exist, raises StateValidationError.
        
        Parameters:
            session (FixSession): The session to validate.
        
        Returns:
            bool: `True` if the session state passes validation.
        
        Raises:
            StateValidationError: If the session is marked "completed" while some errors remain unfixed.
        """
        # Example logic:
        if session.state.value == "completed":
            # Validate that all errors are done
            if len(session.completed_errors) < len(session.errors):
                raise StateValidationError(
                    "Session is marked COMPLETED but not all errors are fixed."
                )
        return True
