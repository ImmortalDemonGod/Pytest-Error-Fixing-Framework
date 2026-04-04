"""
Prompt builders for LLM-based test generation — pure domain layer.

No I/O, no subprocess calls. Takes domain objects, returns strings.

Two generation modes:
  - Per-entity (legacy): SYSTEM_PROMPT + build_user_prompt() — one file per entity
  - Module-level (two-phase): ANALYSIS_SYSTEM_PROMPT + build_analysis_prompt()
    then MODULE_SYSTEM_PROMPT + build_module_prompt() — one consolidated file
"""

from src.dev.test_generator.core.models import (
    AnalysisContext,
    GenerationVariant,
    TestableEntity,
)

# ---------------------------------------------------------------------------
# Shared rules injected into both per-entity and module-level prompts
# ---------------------------------------------------------------------------

_SHARED_RULES = """\
## Rules
1. Import targets using their exact dotted module paths.
2. Write example-based tests with real assertions (assert result == expected).
3. Cover the happy path, edge cases, and error conditions visible from the source.
4. Use pytest.mark.parametrize for multiple similar inputs.
5. Use pytest.raises ONLY when the exception ESCAPES to the caller — i.e.
   the function has a `raise` that is NOT caught by a surrounding try/except
   inside the same function. If the function has a top-level `try/except Exception`
   block and returns `(bool, value)`, it swallows ALL exceptions — never use
   pytest.raises on such a function.
6. Do NOT use Hypothesis or property-based testing — write concrete examples.
7. Do NOT mock the target function itself — test real behaviour.
8. Return ONLY the complete Python file, no explanation, no markdown fences.
9. Match actual constructor signatures exactly. Never omit required arguments.
   Read the Dependency definitions section to see constructors for imported types.
10. For mocking use `unittest.mock.patch` as a context manager or decorator,
    or `patch.object(instance, 'method_name', side_effect=SomeException())`.
    Do NOT replace private methods with lambdas — use patch.object with
    side_effect to simulate failures.
11. When testing syntax error handling use ACTUALLY invalid Python syntax.
    Python syntax is checked at COMPILE time — bare identifiers like
    `"invalid_syntax"` are valid Python (name expressions) and do NOT raise
    SyntaxError. Use: `"x = )"` or `"def foo(:"` or `"print('hello'"`.
12. When testing file-operating functions, ALWAYS write content to the file
    before calling the function. A bare `tmp_path / "f.py"` (never written)
    will fail with "file not found" before the test logic runs.
13. When using `side_effect=function` with `patch` or `monkeypatch.setattr`,
    the side_effect function MUST accept `*args, **kwargs` (or match the exact
    signature of the patched function including `self` for class-level patches).
    Class-level patches (`monkeypatch.setattr(ClassName, "method", fn)`) pass
    `self` as the first argument — a function with 0 or 1 fixed args will raise
    TypeError. ALWAYS write: `def raise_err(*args, **kwargs): raise SomeError()`
14. When using `patch("module.path.ClassName")`, the ClassName MUST actually
    be an attribute of `module.path` (i.e. imported or defined there). To verify:
    if `module/path.py` contains `from other.module import Foo`, patch as
    `module.path.Foo`. If it only passes Foo as a parameter (no import), patch
    `other.module.Foo` instead and inject the mock as a function argument.
    NEVER patch a name in a module that doesn't import it.
"""

# ---------------------------------------------------------------------------
# Per-entity system prompt (legacy single-entity mode)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""\
You are a Python testing expert who writes high-quality pytest test suites.

## Your goal
Write a complete pytest test file for a single Python function or class.

{_SHARED_RULES}"""

# ---------------------------------------------------------------------------
# Module-level Phase 1: Analysis prompt
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """\
You are a Python testing expert performing pre-test analysis.

Analyze the Python source code and produce a structured test plan.
Do NOT write any test code — only analyze and plan.

For each public class, method, and function write a section:

## [ClassName or FunctionName]
### Code paths
- happy path (lines X–Y): describe what happens and what is returned
- error path (line Z): what triggers it, does the exception escape or get caught?
### Planned tests
- test_[name]: what it verifies → asserts [return value / exception / side effect]
### Fixtures / setup needed
- list what must be created or mocked before each test

## Critical analysis rules
- If a method contains `except Exception` at the top level, ALL exceptions are
  caught internally. Plan to assert on the (bool, value) return — NOT pytest.raises.
- When a file must exist for a test (e.g. to be backed up), note that the fixture
  must WRITE content to it first.
- "Syntax error" tests must use code like `"x = )"` or `"def foo(:"`. A bare
  identifier name is valid Python syntax and will not raise SyntaxError.
- Read constructor signatures carefully. Note all required arguments.
"""


def build_analysis_prompt(
    context: AnalysisContext,
    hypothesis_templates: dict[str, str],
    module_dotpath: str = "",
) -> str:
    """Build the Phase 1 analysis request for a whole module.

    Parameters
    ----------
    context:
        Full static-analysis context for the source file.
    hypothesis_templates:
        Maps ``"EntityName.variant"`` → hypothesis scaffold code. Used to
        show the LLM correct import and call signatures during analysis.
    module_dotpath:
        Dotted import path of the source module, e.g. ``"dev.cli.generate"``.
        When provided, included in the prompt so the LLM uses the correct path.
    """
    sections: list[str] = []

    if module_dotpath:
        sections.append(
            f"## Module under test\n"
            f"Import this module with: `import {module_dotpath}` or "
            f"`from {module_dotpath} import <name>`\n"
            f"Do NOT invent a different module path."
        )

    if context.source_code:
        sections.append(
            f"## Source code to analyze\n```python\n{context.source_code}\n```"
        )

    if context.dependency_code:
        sections.append(
            f"## Dependency definitions\n"
            f"Constructor signatures for types imported by this module:\n"
            f"```python\n{context.dependency_code}\n```"
        )

    if context.coverage_gaps:
        gap_lines = []
        for gap in context.coverage_gaps:
            lines = ", ".join(str(ln) for ln in gap.uncovered_lines)
            gap_lines.append(f"- `{gap.entity_name}`: lines {lines}")
        sections.append(
            "## Coverage gaps (lines not yet covered by existing tests)\n"
            + "\n".join(gap_lines)
            + "\nEnsure your test plan covers these lines."
        )

    if hypothesis_templates:
        scaffolds = "\n\n".join(
            f"# {name}\n```python\n{code}\n```"
            for name, code in hypothesis_templates.items()
        )
        sections.append(
            f"## Hypothesis scaffolds (reference only — shows correct imports/signatures)\n"
            f"{scaffolds}"
        )

    sections.append(
        "## Task\nProduce a structured test plan for every public class, method, "
        "and function in the source above. Follow the format described in your instructions."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Module-level Phase 2: Writing prompt
# ---------------------------------------------------------------------------

MODULE_SYSTEM_PROMPT = f"""\
You are a Python testing expert who writes high-quality pytest test suites.

## Your goal
Write a SINGLE consolidated pytest test module for an entire Python source file.

## Structure
- One `class Test<EntityName>` per public class/function being tested.
- Within each class, order tests: happy path → edge cases → error handling.
- Module-level fixtures shared across test classes (e.g. `change_applier`, `test_file`).
- Full import section at the top.

{_SHARED_RULES}"""


def build_module_prompt(
    context: AnalysisContext,
    plan: str,
    hypothesis_templates: dict[str, str],
    module_dotpath: str = "",
) -> str:
    """
    Builds the phase‑2 prompt requesting a single consolidated pytest test module from a phase‑1 plan.
    
    Constructs a prompt that combines, when present, an explicit module import instruction (using `module_dotpath`), the module source, dependency constructor definitions, formatted coverage gaps that must be exercised, the provided analysis `plan`, and optional Hypothesis scaffold examples. The prompt ends with a task instructing the model to return only the Python test module source.
    
    Parameters:
        context (AnalysisContext): Static-analysis context containing optional `source_code`, `dependency_code`, and `coverage_gaps`.
        plan (str): Structured test plan produced by the analysis phase.
        hypothesis_templates (dict[str, str]): Mapping of scaffold names to reference scaffold code showing correct import/call signatures.
        module_dotpath (str): Exact dotted import path for the source module (e.g. "dev.cli.generate"); when provided, the prompt instructs using this path verbatim.
    
    Returns:
        str: The complete prompt string to send to the LLM for writing the consolidated pytest test module.
    """
    sections: list[str] = []

    if module_dotpath:
        sections.append(
            f"## Module under test\n"
            f"**IMPORTANT**: Use `import {module_dotpath}` or "
            f"`from {module_dotpath} import <name>` — this is the EXACT import path. "
            f"Never invent a different module path."
        )

    if context.source_code:
        sections.append(f"## Source code\n```python\n{context.source_code}\n```")

    if context.dependency_code:
        sections.append(
            f"## Dependency definitions\n"
            f"Use these EXACT constructors when instantiating imported types:\n"
            f"```python\n{context.dependency_code}\n```"
        )

    if context.coverage_gaps:
        gap_lines = []
        for gap in context.coverage_gaps:
            lines = ", ".join(str(ln) for ln in gap.uncovered_lines)
            gap_lines.append(f"- `{gap.entity_name}`: lines {lines}")
        sections.append(
            "## Coverage gaps — your tests must exercise these lines\n"
            + "\n".join(gap_lines)
        )

    sections.append(f"## Test plan (from analysis phase)\n{plan}")

    if hypothesis_templates:
        scaffolds = "\n\n".join(
            f"# {name}\n```python\n{code}\n```"
            for name, code in hypothesis_templates.items()
        )
        sections.append(
            f"## Hypothesis scaffolds (correct import/call signatures)\n{scaffolds}"
        )

    sections.append(
        "## Task\nWrite the complete consolidated pytest test module following the "
        "test plan above. Return only the Python source, no explanation."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Per-entity user prompt (legacy — kept for hypothesis-only mode)
# ---------------------------------------------------------------------------

_VARIANT_GUIDANCE: dict = {
    GenerationVariant.DEFAULT: "",
    GenerationVariant.ERRORS: (
        "Pay special attention to error conditions. "
        "Test that ValueError and TypeError are raised correctly."
    ),
    GenerationVariant.ROUNDTRIP: (
        "Test the roundtrip property: encoding then decoding should recover "
        "the original value."
    ),
    GenerationVariant.IDEMPOTENT: (
        "Test the idempotent property: applying the function twice should give "
        "the same result as applying it once."
    ),
    GenerationVariant.ERRORS_EQUIVALENT: (
        "Test that two implementations raise the same exceptions on the same inputs."
    ),
    GenerationVariant.BINARY_OP: (
        "Test commutative and associative properties where appropriate."
    ),
}


def build_user_prompt(
    entity: TestableEntity,
    variant: GenerationVariant,
    context: AnalysisContext,
    hypothesis_template: str = "",
) -> str:
    """
    Builds the user prompt instructing the LLM to generate a complete pytest test file for a single target entity.
    
    Parameters:
        entity (TestableEntity): Target testable entity; its `full_path`, `name`, and `entity_type` are included in the prompt.
        variant (GenerationVariant): Selects the testing angle guidance to include (e.g., edge cases, error handling).
        context (AnalysisContext): Analysis information to embed when present (module source, dependency constructor snippets, mypy/ruff issues, and coverage gaps relevant to the entity).
        hypothesis_template (str): Optional Hypothesis-based scaffold to include as a reference for imports and call signatures; the prompt instructs replacing Hypothesis strategies with concrete example-based tests.
    
    Returns:
        str: The assembled multi-section prompt string to send as the user message in legacy per-entity generation mode.
    """
    sections: list[str] = []

    target = entity.full_path
    sections.append(f"## Target\n`{target}` ({entity.entity_type})")

    guidance = _VARIANT_GUIDANCE.get(variant, "")
    if guidance:
        sections.append(f"## Testing angle\n{guidance}")

    if context.source_code:
        sections.append(f"## Source code\n```python\n{context.source_code}\n```")

    if context.dependency_code:
        sections.append(
            f"## Dependency definitions\n"
            f"Use their exact constructors when writing tests:\n"
            f"```python\n{context.dependency_code}\n```"
        )

    if context.mypy_issues:
        issues = "\n".join(f"- {i}" for i in context.mypy_issues)
        sections.append(f"## Mypy issues\n{issues}")

    if context.ruff_issues:
        issues = "\n".join(f"- {i}" for i in context.ruff_issues)
        sections.append(f"## Ruff issues\n{issues}")

    entity_gaps = _relevant_gaps(entity, context)
    if entity_gaps:
        lines = ", ".join(str(ln) for ln in entity_gaps)
        sections.append(
            f"## Coverage gaps\n"
            f"These lines in `{entity.name}` are not covered by existing tests: {lines}\n"
            "Make sure your tests exercise these lines."
        )

    if hypothesis_template:
        sections.append(
            f"## Scaffold\nUse this as a reference for correct imports and call "
            f"signatures, but replace the Hypothesis `@given` tests with concrete "
            f"example-based pytest tests:\n```python\n{hypothesis_template}\n```"
        )

    sections.append(
        "## Task\nWrite a complete pytest test file for the target above. "
        "Return only the Python source, no explanation."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _relevant_gaps(entity: TestableEntity, context: AnalysisContext) -> tuple:
    """
    Collect uncovered source line numbers associated with the given testable entity.
    
    Checks gaps recorded for the entity's simple name and, if present, the parent-qualified name
    (`{parent_class}.{name}`), then returns the unique line numbers sorted in ascending order.
    
    Parameters:
        entity (TestableEntity): The target entity whose coverage gaps to query.
        context (AnalysisContext): Analysis context providing `gaps_for(name)` to retrieve gap info.
    
    Returns:
        tuple[int]: Sorted tuple of unique uncovered line numbers relevant to the entity.
    """
    names_to_check = [entity.name]
    if entity.parent_class:
        names_to_check.append(f"{entity.parent_class}.{entity.name}")

    all_lines: list[int] = []
    for name in names_to_check:
        gap = context.gaps_for(name)
        if gap:
            all_lines.extend(gap.uncovered_lines)

    return tuple(sorted(set(all_lines)))
