Persistence

Add storage/ directory with:

    session_store.py - Session persistence
    state_manager.py - State handling
    recovery.py - Error recoveryclass SessionStore:
    """Handles persistent storage of fix sessions."""
    
    def __init__(self):
        """Initialize the session store."""
        pass

    def save_session(self, session_data):
        """Save session data."""
        pass

    def load_session(self, session_id):
        """Load session data."""
        pass
