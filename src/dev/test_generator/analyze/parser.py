"""
AST-based parser for Python source files.

Promoted from scripts/hypot_test_gen.py (ModuleParser class).
Produces a ParsedModule value object containing all testable entities.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional

from src.dev.test_generator.core.models import ParsedModule, TestableEntity


def _module_dotpath_from_path(source_path: Path) -> str:
    """Derive a dotted module path from a filesystem path.

    Strategy (matches the original scripts/hypot_test_gen.py construct_module_path):
    1. If the path contains a ``src/`` segment, take everything after it and
       convert to dotted notation — this handles the standard src-layout where
       top-level packages live directly under src/ without their own __init__.py.
    2. Otherwise walk upward through __init__.py boundaries to find the package
       root, then convert the remaining parts.

    Examples
    --------
    ``src/branch_fixer/core/models.py`` → ``branch_fixer.core.models``
    ``scripts/hypot_test_gen.py`` → ``hypot_test_gen``
    """
    resolved = source_path.resolve()
    parts = resolved.parts  # absolute parts including filesystem root

    # Strategy 1: src-layout — take everything after the last 'src' segment
    if "src" in parts:
        src_index = len(parts) - 1 - parts[::-1].index("src")
        module_parts = list(parts[src_index + 1 :])
        return ".".join(p.replace(".py", "") for p in module_parts)

    # Strategy 2: walk __init__.py boundaries upward
    package_parts: List[str] = []
    current = resolved.parent
    while (current / "__init__.py").exists():
        package_parts.insert(0, current.name)
        current = current.parent
    module_name = resolved.stem
    return ".".join(package_parts + [module_name]) if package_parts else module_name


class ModuleParser(ast.NodeVisitor):
    """AST visitor that collects all public, testable entities from a module."""

    # Magic/special method names that are not worth generating tests for.
    _SKIP_METHODS = frozenset({"__init__", "__str__", "__repr__", "property"})

    def __init__(self) -> None:
        """
        Initialize parser internal state.
        
        Sets up:
        - _entities: list collecting discovered TestableEntity objects during AST traversal.
        - _current_class: name of the class currently being visited or None when not inside a class.
        - _class_bases: mapping from class name to a list of its base class names (as extracted from the AST).
        """
        self._entities: List[TestableEntity] = []
        self._current_class: Optional[str] = None
        self._class_bases: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, source_path: Path) -> ParsedModule:
        """
        Parse the Python source file at `source_path` and produce a ParsedModule describing its public testable entities.
        
        Parameters:
            source_path (Path): Filesystem path to the Python source file to analyze.
        
        Returns:
            ParsedModule: Contains `source_path`, the computed module dotted path, and a tuple of discovered `TestableEntity` objects with their `module_path` populated.
        """
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
        self.visit(tree)
        module_dotpath = _module_dotpath_from_path(source_path)
        # Attach dotpath to each entity now that we know it
        entities = tuple(
            TestableEntity(
                name=e.name,
                module_path=module_dotpath,
                entity_type=e.entity_type,
                parent_class=e.parent_class,
            )
            for e in self._entities
        )
        return ParsedModule(
            source_path=source_path,
            module_dotpath=module_dotpath,
            entities=entities,
        )

    # ------------------------------------------------------------------
    # AST visitor methods
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        Visit a top-level class definition and record it as a public testable entity.
        
        Records the class name and its base classes for later use, sets the parser's current class while visiting the class body so contained methods are attributed to it, and ignores classes whose names start with an underscore.
        
        Parameters:
            node (ast.ClassDef): The AST node representing the class definition.
        """
        if node.name.startswith("_"):
            return
        self._store_class_bases(node)
        self._entities.append(
            TestableEntity(name=node.name, module_path="", entity_type="class")
        )
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Collects public function definitions and records them as top-level entities or delegates to method handling when inside a class.
        
        Skips any function whose name starts with an underscore; if currently visiting a class, forwards the node to the method visitor, otherwise appends a `TestableEntity` for the top-level function.
        """
        if node.name.startswith("_"):
            return
        if self._current_class:
            self._visit_method(node)
        else:
            self._entities.append(
                TestableEntity(name=node.name, module_path="", entity_type="function")
            )

    # async defs behave the same for our purposes
    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _store_class_bases(self, node: ast.ClassDef) -> None:
        """
        Record the simple textual names of the given class node's base classes into the parser's class-base map.
        
        Only base names that `_base_name` can resolve (e.g., plain names like `Base` or dotted forms where the left-hand part is an `ast.Name`, such as `pkg.Base`) are collected. The resulting list of base names is stored in `self._class_bases` keyed by the class's name.
        
        Parameters:
            node (ast.ClassDef): The class AST node whose bases will be inspected and recorded.
        """
        bases: List[str] = []
        for base in node.bases:
            name = self._base_name(base)
            if name:
                bases.append(name)
        self._class_bases[node.name] = bases

    @staticmethod
    def _base_name(base: ast.AST) -> Optional[str]:
        """
        Extract the dotted name of a class base from an AST node.
        
        Parameters:
            base (ast.AST): An AST node representing a class base expression.
        
        Returns:
            Optional[str]: The base name (e.g., "Base" or "module.Base") when it can be determined, `None` otherwise.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            return f"{base.value.id}.{base.attr}"
        return None

    def _visit_method(self, node: ast.FunctionDef) -> None:
        """
        Record the given function AST node as a class method TestableEntity when it should be collected, classifying it as an `instance_method` (no `@classmethod`/`@staticmethod` decorators) or `method` (with those decorators).
        
        Parameters:
            node (ast.FunctionDef): The function definition AST node representing the method to evaluate and potentially record.
        
        """
        if self._should_skip(node):
            return
        is_instance = all(
            not (isinstance(d, ast.Name) and d.id in {"classmethod", "staticmethod"})
            for d in node.decorator_list
        )
        entity_type = "instance_method" if is_instance else "method"
        self._entities.append(
            TestableEntity(
                name=node.name,
                module_path="",
                entity_type=entity_type,
                parent_class=self._current_class,
            )
        )

    def _should_skip(self, node: ast.FunctionDef) -> bool:
        """
        Decides whether a given function/method AST node should be excluded from entity collection.
        
        Parameters:
            node (ast.FunctionDef): The function or method AST node to evaluate.
        
        Returns:
            bool: `True` if the node should be skipped (name is in the skip list or it's a `visit_...` method on a class inheriting from `NodeVisitor`), `False` otherwise.
        """
        if node.name in self._SKIP_METHODS:
            return True
        current_bases = self._class_bases.get(self._current_class or "", [])
        if any(b in {"NodeVisitor", "ast.NodeVisitor"} for b in current_bases):
            if node.name.startswith("visit_"):
                return True
        return False
