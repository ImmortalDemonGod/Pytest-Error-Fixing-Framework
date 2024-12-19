class FixOrchestratorError(Exception):
    """Base exception for orchestrator errors"""
    pass

class SessionError(FixOrchestratorError):
    """Raised when session operations fail"""
    pass

class FixAttemptError(FixOrchestratorError):
    """Raised when fix attempts fail"""
    pass


class FixServiceError(Exception):
    """Base exception for fix service errors"""
    pass