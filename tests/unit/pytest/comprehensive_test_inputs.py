# src/branch_fixer/services/pytest/comprehensive_test_inputs.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union
import json
import math

@dataclass
class DataPoint:
    """A sample data point class for test generation"""
    x: float
    y: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        # Introduce a bug: Convert metadata from a dictionary to a list of keys
        if self.metadata is not None:
            self.metadata = list(self.metadata.keys())

class MathOperations:
    """A class demonstrating various mathematical operations"""
    
    def __init__(self, precision: int = 2):
        self.precision = precision
    
    @staticmethod
    def add(a: float, b: float) -> float:
        """Binary addition operation"""
        return a + b
    
    @classmethod
    def create_with_default_precision(cls) -> 'MathOperations':
        """Factory method returning default instance"""
        return cls(precision=2)
        
    def transform_point(self, point: DataPoint) -> DataPoint:
        """Transform a point using some math operations"""
        return DataPoint(
            x=round(point.x * math.cos(math.pi/4), self.precision),
            y=round(point.y * math.sin(math.pi/4), self.precision),
            label=point.label,
            metadata=point.metadata
        )
        
    def validate_point(self, point: DataPoint) -> bool:
        """Check if point is in valid range"""
        if not isinstance(point, DataPoint):
            raise TypeError("Input must be a DataPoint")
        if abs(point.x) > 1000 or abs(point.y) > 1000:
            raise ValueError("Point coordinates must be within [-1000, 1000]")
        return True

class DataEncoder:
    """Class demonstrating encoding/decoding operations"""
    
    def encode_point(self, point: DataPoint) -> str:
        """Encode a data point to JSON string"""
        return json.dumps({
            'x': point.x,
            'y': point.y,
            'label': point.label,
            'metadata': point.metadata
        })
    
    def decode_point(self, data: str) -> DataPoint:
        """Decode JSON string to data point"""
        try:
            obj = json.loads(data)
            return DataPoint(
                x=obj['x'],
                y=obj['y'],
                label=obj.get('label'),
                metadata=obj.get('metadata')
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid point data: {e}")

class PathProcessor:
    """Class for path processing operations"""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        
    def combine_paths(self, path1: Union[str, Path], path2: Union[str, Path]) -> Path:
        """Combine two paths - good for testing binary operations"""
        return Path(path1) / Path(path2)
        
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path - good for testing idempotent operations"""
        return Path(path).resolve()
    
    def verify_path(self, path: Union[str, Path]) -> bool:
        """Verify path exists - good for testing validation"""
        path_obj = Path(path)
        if not path_obj.exists():
            raise ValueError(f"Path does not exist: {path}")
        return True
    
    def list_directory(self, path: Union[str, Path]) -> Set[Path]:
        """List directory contents - good for testing complex returns"""
        path_obj = Path(path)
        if not path_obj.is_dir():
            raise ValueError(f"Not a directory: {path}")
        return {p for p in path_obj.iterdir() if not p.name.startswith('.')}
