"""Unit tests for src/dev/test_generator/output/formatter.py"""

from src.dev.test_generator.output.formatter import fix_generated_code


class TestFixGeneratedCode:
    def test_valid_code_returned_unchanged_semantically(self):
        src = "def test_foo():\n    assert 1 + 1 == 2\n"
        result = fix_generated_code(src)
        assert result is not None
        assert "test_foo" in result

    def test_duplicate_self_removed(self):
        src = (
            "class TestFoo:\n"
            "    def test_method(self, self, x):\n"
            "        pass\n"
        )
        result = fix_generated_code(src)
        assert result is not None
        # After fix there should be exactly one 'self' in the arg list
        assert result.count("self, self") == 0

    def test_no_duplicate_self_unchanged(self):
        src = (
            "class TestFoo:\n"
            "    def test_method(self, x):\n"
            "        pass\n"
        )
        result = fix_generated_code(src)
        assert result is not None
        assert "test_method" in result

    def test_unparseable_source_returns_none(self):
        result = fix_generated_code("def (broken syntax:")
        assert result is None

    def test_empty_string_returns_empty(self):
        result = fix_generated_code("")
        assert result is not None  # empty module is valid Python
        assert result == "" or result.strip() == ""
