# branch_fixer/orchestration/progress.py
from branch_fixer.orchestrator import FixSession

class ProgressReporter:
    """Reports progress of fix operations"""
    
    def __init__(self, session: FixSession):
        """Initialize reporter
        
        Args:
            session: Session to track
            
        Raises:
            ValueError: If session invalid
        """
        raise NotImplementedError()

    def update_progress(self, message: str) -> None:
        """Update progress with new message
        
        Args:
            message: Progress message
            
        Raises:
            RuntimeError: If session completed/failed
        """
        raise NotImplementedError()
        
    def show_summary(self) -> None:
        """Show session summary
        
        Raises:
            RuntimeError: If session not completed
        """
        raise NotImplementedError()
