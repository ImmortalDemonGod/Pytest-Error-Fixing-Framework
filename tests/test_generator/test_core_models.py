import pytest
from pathlib import Path
from uuid import UUID

from src.dev.test_generator.core.models import (
    AnalysisContext,
    CoverageGap,
    GenerationAttempt,
    GenerationConfig,
    GenerationRequest,
    GenerationVariant,
    ParsedModule,
    TestableEntity,
)


# ---------------------------------------------------------------------------
# CoverageGap
# ---------------------------------------------------------------------------


class TestCoverageGap:
    def test_is_frozen(self):
        gap = CoverageGap(entity_name="add", uncovered_lines=(10, 11))
        with pytest.raises((AttributeError, TypeError)):
            gap.entity_name = "changed"  # type: ignore[misc]

    def test_equality_by_value(self):
        g1 = CoverageGap("add", (10, 11))
        g2 = CoverageGap("add", (10, 11))
        assert g1 == g2

    def test_is_empty_true_when_no_lines(self):
        gap = CoverageGap(entity_name="add", uncovered_lines=())
        assert gap.is_empty is True

    def test_is_empty_false_when_lines_present(self):
        gap = CoverageGap(entity_name="add", uncovered_lines=(5,))
        assert gap.is_empty is False

    def test_different_names_not_equal(self):
        assert CoverageGap("add", (1,)) != CoverageGap("sub", (1,))


# ---------------------------------------------------------------------------
# AnalysisContext
# ---------------------------------------------------------------------------


class TestAnalysisContext:
    def _gap(self, name: str, *lines: int) -> CoverageGap:
        return CoverageGap(entity_name=name, uncovered_lines=tuple(lines))

    def test_is_frozen(self):
        ctx = AnalysisContext.empty("x = 1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.source_code = "changed"  # type: ignore[misc]

    def test_empty_factory_source_code(self):
        ctx = AnalysisContext.empty("def add(a, b): return a + b")
        assert ctx.source_code == "def add(a, b): return a + b"

    def test_empty_factory_no_issues(self):
        ctx = AnalysisContext.empty("x = 1")
        assert ctx.mypy_issues == ()
        assert ctx.ruff_issues == ()
        assert ctx.coverage_gaps == ()

    def test_has_coverage_gaps_false_when_empty(self):
        ctx = AnalysisContext.empty("x = 1")
        assert ctx.has_coverage_gaps() is False

    def test_has_coverage_gaps_false_when_all_gaps_empty(self):
        ctx = AnalysisContext(
            source_code="x = 1",
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(self._gap("add"),),  # uncovered_lines=()
        )
        assert ctx.has_coverage_gaps() is False

    def test_has_coverage_gaps_true_when_any_uncovered(self):
        ctx = AnalysisContext(
            source_code="x = 1",
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(self._gap("add", 10, 11),),
        )
        assert ctx.has_coverage_gaps() is True

    def test_gaps_for_returns_matching(self):
        gap = self._gap("compute", 5, 6)
        ctx = AnalysisContext(
            source_code="x = 1",
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(gap,),
        )
        assert ctx.gaps_for("compute") == gap

    def test_gaps_for_returns_none_when_no_match(self):
        ctx = AnalysisContext.empty("x = 1")
        assert ctx.gaps_for("nonexistent") is None

    def test_gaps_for_matches_exact_name(self):
        gap_add = self._gap("add", 1)
        gap_sub = self._gap("sub", 2)
        ctx = AnalysisContext(
            source_code="x = 1",
            mypy_issues=(),
            ruff_issues=(),
            coverage_gaps=(gap_add, gap_sub),
        )
        assert ctx.gaps_for("sub") == gap_sub
        assert ctx.gaps_for("add") == gap_add

    def test_carries_mypy_and_ruff_issues(self):
        ctx = AnalysisContext(
            source_code="x = 1",
            mypy_issues=('error: Missing return statement',),
            ruff_issues=('F401 imported but unused',),
            coverage_gaps=(),
        )
        assert len(ctx.mypy_issues) == 1
        assert len(ctx.ruff_issues) == 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_entity():
    return TestableEntity(
        name="add",
        module_path="mypackage.math_ops",
        entity_type="function",
    )


@pytest.fixture
def class_method_entity():
    return TestableEntity(
        name="encode",
        module_path="mypackage.codec",
        entity_type="instance_method",
        parent_class="Codec",
    )


@pytest.fixture
def parsed_module(sample_entity, class_method_entity):
    return ParsedModule(
        source_path=Path("src/mypackage/math_ops.py"),
        module_dotpath="mypackage.math_ops",
        entities=(sample_entity, class_method_entity),
    )


@pytest.fixture
def config():
    return GenerationConfig(
        output_dir=Path("generated_tests"),
        strategy_name="hypothesis",
    )


@pytest.fixture
def request_obj(parsed_module, config):
    return GenerationRequest(parsed_module=parsed_module, config=config)


# ---------------------------------------------------------------------------
# TestableEntity
# ---------------------------------------------------------------------------


class TestTestableEntity:
    def test_full_path_standalone_function(self, sample_entity):
        assert sample_entity.full_path == "mypackage.math_ops.add"

    def test_full_path_with_parent_class(self, class_method_entity):
        assert class_method_entity.full_path == "mypackage.codec.Codec.encode"

    def test_is_frozen(self, sample_entity):
        with pytest.raises((AttributeError, TypeError)):
            sample_entity.name = "changed"  # type: ignore[misc]

    def test_equality_by_value(self):
        e1 = TestableEntity("foo", "pkg.mod", "function")
        e2 = TestableEntity("foo", "pkg.mod", "function")
        assert e1 == e2


# ---------------------------------------------------------------------------
# ParsedModule
# ---------------------------------------------------------------------------


class TestParsedModule:
    def test_entities_of_type_returns_matching(self, parsed_module, sample_entity):
        funcs = parsed_module.entities_of_type("function")
        assert sample_entity in funcs

    def test_entities_of_type_excludes_non_matching(self, parsed_module, class_method_entity):
        funcs = parsed_module.entities_of_type("function")
        assert class_method_entity not in funcs

    def test_entities_of_type_empty_when_no_match(self, parsed_module):
        classes = parsed_module.entities_of_type("class")
        assert classes == []


# ---------------------------------------------------------------------------
# GenerationVariant
# ---------------------------------------------------------------------------


class TestGenerationVariant:
    def test_all_variants_accessible(self):
        assert GenerationVariant.ROUNDTRIP.value == "roundtrip"
        assert GenerationVariant.IDEMPOTENT.value == "idempotent"
        assert GenerationVariant.ERRORS_EQUIVALENT.value == "errors_equivalent"
        assert GenerationVariant.BINARY_OP.value == "binary_op"
        assert GenerationVariant.DEFAULT.value == "default"


# ---------------------------------------------------------------------------
# GenerationAttempt
# ---------------------------------------------------------------------------


class TestGenerationAttempt:
    def test_initial_state(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        assert attempt.status == "pending"
        assert attempt.generated_code is None
        assert attempt.error_message is None
        assert isinstance(attempt.id, UUID)

    def test_mark_success(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        attempt.mark_success("def test_add(): pass")
        assert attempt.status == "success"
        assert attempt.generated_code == "def test_add(): pass"

    def test_mark_failed(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        attempt.mark_failed("hypothesis not installed")
        assert attempt.status == "failed"
        assert attempt.error_message == "hypothesis not installed"

    def test_mark_skipped(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        attempt.mark_skipped("entity type not supported")
        assert attempt.status == "skipped"

    def test_mark_success_from_success_raises(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        attempt.mark_success("code")
        with pytest.raises(ValueError, match="Cannot mark success"):
            attempt.mark_success("more code")

    def test_to_dict_contains_required_keys(self, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.ROUNDTRIP)
        d = attempt.to_dict()
        assert d["entity_name"] == "add"
        assert d["variant"] == "roundtrip"
        assert d["status"] == "pending"
        assert "id" in d


# ---------------------------------------------------------------------------
# GenerationRequest (aggregate root)
# ---------------------------------------------------------------------------


class TestGenerationRequest:
    def test_initial_state(self, request_obj):
        assert request_obj.status == "pending"
        assert request_obj.attempts == []
        assert isinstance(request_obj.id, UUID)

    def test_start_transitions_to_in_progress(self, request_obj):
        request_obj.start()
        assert request_obj.status == "in_progress"

    def test_start_twice_raises(self, request_obj):
        request_obj.start()
        with pytest.raises(ValueError, match="Cannot start"):
            request_obj.start()

    def test_add_attempt_requires_in_progress(self, request_obj, sample_entity):
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        with pytest.raises(ValueError, match="in_progress"):
            request_obj.add_attempt(attempt)

    def test_add_attempt_success(self, request_obj, sample_entity):
        request_obj.start()
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        request_obj.add_attempt(attempt)
        assert len(request_obj.attempts) == 1

    def test_complete_transitions_status(self, request_obj, sample_entity):
        request_obj.start()
        attempt = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        attempt.mark_success("code")
        request_obj.add_attempt(attempt)
        request_obj.complete()
        assert request_obj.status == "completed"

    def test_complete_from_wrong_state_raises(self, request_obj):
        with pytest.raises(ValueError, match="Cannot complete"):
            request_obj.complete()

    def test_fail_sets_status(self, request_obj):
        request_obj.fail()
        assert request_obj.status == "failed"

    def test_successful_attempts_filters_correctly(self, request_obj, sample_entity, class_method_entity):
        request_obj.start()
        a1 = GenerationAttempt(entity=sample_entity, variant=GenerationVariant.DEFAULT)
        a2 = GenerationAttempt(entity=class_method_entity, variant=GenerationVariant.ROUNDTRIP)
        a1.mark_success("good code")
        a2.mark_failed("oops")
        request_obj.add_attempt(a1)
        request_obj.add_attempt(a2)
        assert request_obj.successful_attempts == [a1]
        assert request_obj.failed_attempts == [a2]

    def test_to_dict_shape(self, request_obj):
        d = request_obj.to_dict()
        assert d["strategy_name"] == "hypothesis"
        assert d["status"] == "pending"
        assert d["attempts"] == []
        assert "id" in d
        assert "source_path" in d
