# branch_fixer/core/exceptions.py
class FixError(Exception):
    """Base exception for fix operations"""
    pass

class CoordinationError(FixError):
    """Errors related to coordination"""
    pass

class WorkflowError(FixError):
    """Errors related to workflow dispatching"""
    pass

class ComponentError(FixError):
    """Errors related to specific components"""
    pass

class InteractionError(FixError):
    """Errors related to component interactions"""
    pass
