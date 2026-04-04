"""Unit tests for src/dev/test_generator/analyze/parser.py"""

import textwrap
from pathlib import Path

import pytest

from src.dev.test_generator.analyze.parser import ModuleParser, _module_dotpath_from_path
from src.dev.test_generator.core.models import ParsedModule, TestableEntity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_source(tmp_path: Path, source: str, filename: str = "mymod.py") -> ParsedModule:
    """
    Write `source` to a file named `filename` located under `tmp_path`, parse that file, and return the resulting ParsedModule.
    
    Parameters:
        tmp_path (Path): Directory in which to create the temporary file (typically pytest's tmp_path).
        source (str): Python source code to write; it will be dedented before writing.
        filename (str): Name of the file to create under `tmp_path` (default "mymod.py").
    
    Returns:
        ParsedModule: The parsed representation of the module defined by the written file.
    """
    f = tmp_path / filename
    f.write_text(textwrap.dedent(source), encoding="utf-8")
    return ModuleParser().parse(f)


# ---------------------------------------------------------------------------
# _module_dotpath_from_path
# ---------------------------------------------------------------------------


class TestModuleDotpath:
    def test_standalone_file(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("")
        assert _module_dotpath_from_path(f) == "mymod"

    def test_package_file_via_init(self, tmp_path):
        """Falls back to __init__.py walking when there's no src/ segment."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        mod = pkg / "utils.py"
        mod.write_text("")
        result = _module_dotpath_from_path(mod)
        assert result == "mypkg.utils"

    def test_src_layout_takes_everything_after_src(self, tmp_path):
        """src-layout: take all parts after src/, regardless of __init__.py."""
        src = tmp_path / "src"
        pkg = src / "mypkg" / "core"
        pkg.mkdir(parents=True)
        mod = pkg / "models.py"
        mod.write_text("")
        result = _module_dotpath_from_path(mod)
        assert result == "mypkg.core.models"

    def test_src_layout_no_init_needed(self, tmp_path):
        """Top-level package under src/ without __init__.py still works."""
        src = tmp_path / "src"
        pkg = src / "branch_fixer" / "core"
        pkg.mkdir(parents=True)
        # No __init__.py anywhere
        mod = pkg / "models.py"
        mod.write_text("")
        result = _module_dotpath_from_path(mod)
        assert result == "branch_fixer.core.models"


# ---------------------------------------------------------------------------
# Standalone functions
# ---------------------------------------------------------------------------


class TestStandaloneFunctions:
    def test_public_function_discovered(self, tmp_path):
        pm = _parse_source(tmp_path, """
            def add(a, b):
                return a + b
        """)
        names = [e.name for e in pm.entities]
        assert "add" in names

    def test_private_function_skipped(self, tmp_path):
        pm = _parse_source(tmp_path, """
            def _helper():
                pass
        """)
        assert pm.entities == ()

    def test_multiple_functions(self, tmp_path):
        pm = _parse_source(tmp_path, """
            def foo(): pass
            def bar(): pass
            def _skip(): pass
        """)
        names = {e.name for e in pm.entities}
        assert names == {"foo", "bar"}

    def test_entity_type_is_function(self, tmp_path):
        pm = _parse_source(tmp_path, "def greet(name): return f'hi {name}'")
        assert pm.entities[0].entity_type == "function"

    def test_module_path_filled_in(self, tmp_path):
        pm = _parse_source(tmp_path, "def greet(): pass")
        assert pm.entities[0].module_path == "mymod"


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


class TestClasses:
    def test_public_class_discovered(self, tmp_path):
        pm = _parse_source(tmp_path, "class Foo: pass")
        names = [e.name for e in pm.entities]
        assert "Foo" in names

    def test_private_class_skipped(self, tmp_path):
        pm = _parse_source(tmp_path, "class _Hidden: pass")
        assert pm.entities == ()

    def test_class_entity_type(self, tmp_path):
        pm = _parse_source(tmp_path, "class MyClass: pass")
        cls_entities = [e for e in pm.entities if e.entity_type == "class"]
        assert len(cls_entities) == 1


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


class TestMethods:
    def test_instance_method_discovered(self, tmp_path):
        pm = _parse_source(tmp_path, """
            class Calc:
                def add(self, a, b):
                    return a + b
        """)
        methods = [e for e in pm.entities if e.entity_type == "instance_method"]
        assert any(m.name == "add" for m in methods)

    def test_instance_method_parent_class_set(self, tmp_path):
        pm = _parse_source(tmp_path, """
            class Calc:
                def add(self, a, b): pass
        """)
        method = next(e for e in pm.entities if e.name == "add")
        assert method.parent_class == "Calc"

    def test_static_method_entity_type(self, tmp_path):
        pm = _parse_source(tmp_path, """
            class Util:
                @staticmethod
                def helper(x): pass
        """)
        method = next(e for e in pm.entities if e.name == "helper")
        assert method.entity_type == "method"  # not instance_method

    def test_dunder_methods_skipped(self, tmp_path):
        pm = _parse_source(tmp_path, """
            class Foo:
                def __init__(self): pass
                def __str__(self): return 'foo'
                def public(self): pass
        """)
        names = [e.name for e in pm.entities]
        assert "__init__" not in names
        assert "__str__" not in names
        assert "public" in names

    def test_private_method_skipped(self, tmp_path):
        pm = _parse_source(tmp_path, """
            class Foo:
                def _private(self): pass
                def public(self): pass
        """)
        names = [e.name for e in pm.entities]
        assert "_private" not in names
        assert "public" in names


# ---------------------------------------------------------------------------
# NodeVisitor subclass filtering
# ---------------------------------------------------------------------------


class TestNodeVisitorFiltering:
    def test_visit_methods_skipped_for_nodevisitor_subclass(self, tmp_path):
        pm = _parse_source(tmp_path, """
            import ast
            class MyVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node): pass
                def visit_ClassDef(self, node): pass
                def public_util(self): pass
        """)
        names = [e.name for e in pm.entities]
        assert "visit_FunctionDef" not in names
        assert "visit_ClassDef" not in names
        assert "public_util" in names


# ---------------------------------------------------------------------------
# ParsedModule helpers
# ---------------------------------------------------------------------------


class TestParsedModuleHelpers:
    def test_entities_of_type_function(self, tmp_path):
        pm = _parse_source(tmp_path, """
            def foo(): pass
            class Bar:
                def baz(self): pass
        """)
        funcs = pm.entities_of_type("function")
        assert all(e.entity_type == "function" for e in funcs)
        assert any(e.name == "foo" for e in funcs)

    def test_source_path_recorded(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def foo(): pass")
        pm = ModuleParser().parse(f)
        assert pm.source_path == f
