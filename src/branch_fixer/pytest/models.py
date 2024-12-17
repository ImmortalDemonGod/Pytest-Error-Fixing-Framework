# services/pytest/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

@dataclass
class TestResult:
    """Results from a test execution"""
    passed: bool
    output: str
    error_message: Optional[str] = None
    execution_time: float = 0.0
    test_count: int = 0
    failure_count: int = 0
    test_file: Optional[Path] = None
    test_function: Optional[str] = None
    timestamp: datetime = datetime.now()
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}