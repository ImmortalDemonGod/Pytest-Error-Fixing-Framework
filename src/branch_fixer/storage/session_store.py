class SessionStore:
    """Handles persistent storage of fix sessions"""
    
    def __init__(self, storage_dir: Path):
        """Initialize session store
        
        Args:
            storage_dir: Directory to store session data
            
        Raises:
            PermissionError: If directory not writable
            ValueError: If path invalid
        """
        raise NotImplementedError()

    async def save_session(self, session: FixSession) -> None:
        """Save session state to storage
        
        Args:
            session: Session to save
            
        Raises:
            IOError: If save fails
            ValueError: If session invalid
        """
        raise NotImplementedError()

    async def load_session(self, session_id: UUID) -> Optional[FixSession]:
        """Load session from storage
        
        Args:
            session_id: ID of session to load
            
        Returns:
            Loaded FixSession or None if not found
            
        Raises:
            IOError: If load fails
            ValueError: If data corrupt
        """ 
        raise NotImplementedError()
