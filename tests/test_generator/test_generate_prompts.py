"""Unit tests for src/dev/test_generator/generate/prompts.py

All tests are pure (no I/O, no subprocess) — prompts.py is domain-only.
"""

import pytest

from src.dev.test_generator.core.models import (
    AnalysisContext,
    CoverageGap,
    GenerationVariant,
    TestableEntity,
)
from src.dev.test_generator.generate.prompts import (
    SYSTEM_PROMPT,
    _relevant_gaps,
    build_user_prompt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(
    name: str = "add",
    entity_type: str = "function",
    parent: str = None,
    module: str = "pkg.mod",
) -> TestableEntity:
    """
    Create a TestableEntity with the given identifying metadata.
    
    Parameters:
        name (str): Entity name (function or method name). Defaults to "add".
        entity_type (str): Description of the entity kind (e.g., "function", "instance_method"). Defaults to "function".
        parent (str | None): Optional parent class name for methods; use None for standalone functions.
        module (str): Dotted module path where the entity is defined (e.g., "pkg.mod"). Defaults to "pkg.mod".
    
    Returns:
        TestableEntity: An instance representing the specified testable entity.
    """
    return TestableEntity(
        name=name, module_path=module, entity_type=entity_type, parent_class=parent
    )


def _gap(name: str, *lines: int) -> CoverageGap:
    """
    Constructs a CoverageGap for an entity with the specified uncovered line numbers.
    
    Parameters:
        name (str): The entity name as recorded in coverage data (e.g., "func" or "Class.method").
        *lines (int): One or more uncovered line numbers for the entity.
    
    Returns:
        CoverageGap: A CoverageGap with `entity_name` set to `name` and `uncovered_lines` set to a tuple of the provided line numbers in the same order.
    """
    return CoverageGap(entity_name=name, uncovered_lines=tuple(lines))


def _ctx(
    source: str = "def add(a, b): return a + b",
    mypy: tuple = (),
    ruff: tuple = (),
    gaps: tuple = (),
) -> AnalysisContext:
    """
    Create an AnalysisContext populated with the given source, static-analysis issues, and coverage gaps.
    
    Parameters:
        source (str): Source code to include in the context. Defaults to a small `add` function string.
        mypy (tuple): Sequence of mypy issue descriptions to include.
        ruff (tuple): Sequence of ruff issue descriptions to include.
        gaps (tuple): Sequence of CoverageGap instances representing uncovered lines.
    
    Returns:
        AnalysisContext: An AnalysisContext with `source_code`, `mypy_issues`, `ruff_issues`, and `coverage_gaps` set from the corresponding parameters.
    """
    return AnalysisContext(
        source_code=source, mypy_issues=mypy, ruff_issues=ruff, coverage_gaps=gaps
    )


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_is_non_empty_string(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_forbids_hypothesis(self):
        # LLM must not generate Hypothesis tests
        assert "NOT use Hypothesis" in SYSTEM_PROMPT

    def test_requires_real_assertions(self):
        assert "assert" in SYSTEM_PROMPT.lower()

    def test_requires_exact_import(self):
        assert "dotted module path" in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# build_user_prompt — target section
# ---------------------------------------------------------------------------


class TestBuildUserPromptTarget:
    def test_includes_full_path_for_standalone_function(self):
        prompt = build_user_prompt(_entity("add"), GenerationVariant.DEFAULT, _ctx())
        assert "pkg.mod.add" in prompt

    def test_includes_full_path_for_method(self):
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        prompt = build_user_prompt(e, GenerationVariant.DEFAULT, _ctx())
        assert "pkg.mod.Codec.encode" in prompt

    def test_includes_entity_type(self):
        prompt = build_user_prompt(_entity("add"), GenerationVariant.DEFAULT, _ctx())
        assert "function" in prompt


# ---------------------------------------------------------------------------
# build_user_prompt — source code section
# ---------------------------------------------------------------------------


class TestBuildUserPromptSourceCode:
    def test_includes_source_code(self):
        ctx = _ctx(source="def add(a, b): return a + b")
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "def add(a, b): return a + b" in prompt

    def test_wraps_source_in_code_fence(self):
        ctx = _ctx(source="x = 1")
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "```python" in prompt


# ---------------------------------------------------------------------------
# build_user_prompt — variant guidance
# ---------------------------------------------------------------------------


class TestBuildUserPromptVariantGuidance:
    def test_default_variant_has_no_extra_guidance(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert "Testing angle" not in prompt

    def test_errors_variant_mentions_exceptions(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.ERRORS, _ctx())
        assert "ValueError" in prompt or "TypeError" in prompt

    def test_roundtrip_variant_mentions_roundtrip(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.ROUNDTRIP, _ctx())
        assert "roundtrip" in prompt.lower()

    def test_idempotent_variant_mentions_idempotent(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.IDEMPOTENT, _ctx())
        assert "idempotent" in prompt.lower()

    def test_binary_op_variant_mentions_commutative(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.BINARY_OP, _ctx())
        assert "commutative" in prompt.lower() or "associative" in prompt.lower()


# ---------------------------------------------------------------------------
# build_user_prompt — static analysis sections
# ---------------------------------------------------------------------------


class TestBuildUserPromptStaticAnalysis:
    def test_mypy_issues_included_when_present(self):
        ctx = _ctx(mypy=("ops.py:5: error: Missing return statement",))
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "Missing return statement" in prompt

    def test_mypy_section_absent_when_empty(self):
        ctx = _ctx(mypy=())
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "Mypy" not in prompt

    def test_ruff_issues_included_when_present(self):
        ctx = _ctx(ruff=("ops.py:1:1: F401 unused",))
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "F401" in prompt

    def test_ruff_section_absent_when_empty(self):
        ctx = _ctx(ruff=())
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "Ruff" not in prompt


# ---------------------------------------------------------------------------
# build_user_prompt — coverage gaps
# ---------------------------------------------------------------------------


class TestBuildUserPromptCoverageGaps:
    def test_coverage_gap_for_entity_included(self):
        ctx = _ctx(gaps=(_gap("add", 10, 11),))
        prompt = build_user_prompt(_entity("add"), GenerationVariant.DEFAULT, ctx)
        assert "10" in prompt
        assert "11" in prompt

    def test_coverage_section_absent_when_no_gaps(self):
        ctx = _ctx(gaps=())
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, ctx)
        assert "Coverage gaps" not in prompt

    def test_coverage_gap_for_different_entity_not_included(self):
        ctx = _ctx(gaps=(_gap("multiply", 20),))
        prompt = build_user_prompt(_entity("add"), GenerationVariant.DEFAULT, ctx)
        assert "Coverage gaps" not in prompt

    def test_method_gap_matched_by_class_dot_method(self):
        # coverage.py stores method coverage as "ClassName.method_name"
        ctx = _ctx(gaps=(_gap("Codec.encode", 7, 8),))
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        prompt = build_user_prompt(e, GenerationVariant.DEFAULT, ctx)
        assert "7" in prompt
        assert "8" in prompt


# ---------------------------------------------------------------------------
# build_user_prompt — hypothesis template scaffold
# ---------------------------------------------------------------------------


class TestBuildUserPromptScaffold:
    def test_template_included_when_provided(self):
        template = "class TestFuzzAdd(unittest.TestCase):\n    pass"
        prompt = build_user_prompt(
            _entity(), GenerationVariant.DEFAULT, _ctx(), hypothesis_template=template
        )
        assert "TestFuzzAdd" in prompt

    def test_scaffold_section_absent_when_no_template(self):
        prompt = build_user_prompt(
            _entity(), GenerationVariant.DEFAULT, _ctx(), hypothesis_template=""
        )
        assert "Scaffold" not in prompt

    def test_template_wrapped_in_code_fence(self):
        template = "x = 1"
        prompt = build_user_prompt(
            _entity(), GenerationVariant.DEFAULT, _ctx(), hypothesis_template=template
        )
        # There should be at least 2 code fences (source + scaffold)
        assert prompt.count("```python") >= 2


# ---------------------------------------------------------------------------
# build_user_prompt — task section always present
# ---------------------------------------------------------------------------


class TestBuildUserPromptTask:
    def test_task_section_always_present(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert "Task" in prompt

    def test_task_mentions_return_only_python(self):
        prompt = build_user_prompt(_entity(), GenerationVariant.DEFAULT, _ctx())
        assert "only" in prompt.lower()


# ---------------------------------------------------------------------------
# _relevant_gaps helper
# ---------------------------------------------------------------------------


class TestRelevantGaps:
    def test_finds_bare_name_gap(self):
        ctx = _ctx(gaps=(_gap("add", 5),))
        result = _relevant_gaps(_entity("add"), ctx)
        assert 5 in result

    def test_finds_class_dot_method_gap(self):
        ctx = _ctx(gaps=(_gap("Codec.encode", 9),))
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        result = _relevant_gaps(e, ctx)
        assert 9 in result

    def test_merges_both_forms_deduplicated(self):
        # Both "encode" and "Codec.encode" map to the same entity
        ctx = _ctx(gaps=(_gap("encode", 3), _gap("Codec.encode", 3, 5)))
        e = _entity("encode", entity_type="instance_method", parent="Codec")
        result = _relevant_gaps(e, ctx)
        assert sorted(result) == [3, 5]  # 3 deduplicated

    def test_returns_empty_when_no_match(self):
        ctx = _ctx(gaps=(_gap("other", 1),))
        result = _relevant_gaps(_entity("add"), ctx)
        assert result == ()

    def test_returns_sorted_lines(self):
        ctx = _ctx(gaps=(_gap("add", 9, 2, 5),))
        result = _relevant_gaps(_entity("add"), ctx)
        assert list(result) == [2, 5, 9]
