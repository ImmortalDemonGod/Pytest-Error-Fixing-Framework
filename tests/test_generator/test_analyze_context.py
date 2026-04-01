"""Unit tests for src/dev/test_generator/analyze/context.py

Strategy:
- ContextGatherer helpers are tested by patching subprocess.run so tests
  are fast and hermetic.
- find_test_file and parse_coverage_json are pure functions tested with
  real tmp_path fixtures — no mocks needed.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.dev.test_generator.analyze.context import (
    ContextGatherer,
    find_test_file,
    parse_coverage_json,
)
from src.dev.test_generator.core.models import AnalysisContext, CoverageGap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _make_source(tmp_path: Path, name: str = "module.py") -> Path:
    p = tmp_path / name
    p.write_text("def add(a, b): return a + b\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# find_test_file
# ---------------------------------------------------------------------------


class TestFindTestFile:
    def test_finds_test_prefix_sibling(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        test = tmp_path / "test_ops.py"
        test.write_text("", encoding="utf-8")
        assert find_test_file(src) == test

    def test_finds_suffix_sibling(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        test = tmp_path / "ops_test.py"
        test.write_text("", encoding="utf-8")
        assert find_test_file(src) == test

    def test_prefers_prefix_over_suffix_sibling(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        prefix = tmp_path / "test_ops.py"
        suffix = tmp_path / "ops_test.py"
        prefix.write_text("", encoding="utf-8")
        suffix.write_text("", encoding="utf-8")
        assert find_test_file(src) == prefix

    def test_finds_test_in_tests_dir_for_src_layout(self, tmp_path):
        # layout: tmp_path/src/mypkg/ops.py  +  tmp_path/tests/test_ops.py
        src_dir = tmp_path / "src" / "mypkg"
        src_dir.mkdir(parents=True)
        src = src_dir / "ops.py"
        src.write_text("", encoding="utf-8")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test = tests_dir / "test_ops.py"
        test.write_text("", encoding="utf-8")

        assert find_test_file(src) == test

    def test_returns_none_when_no_test_file(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        assert find_test_file(src) is None


# ---------------------------------------------------------------------------
# parse_coverage_json
# ---------------------------------------------------------------------------


class TestParseCoverageJson:
    def _write_json(self, tmp_path: Path, data: dict) -> Path:
        p = tmp_path / "cov.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def _minimal_report(self, file_key: str, functions: dict) -> dict:
        return {"files": {file_key: {"functions": functions, "missing_lines": []}}}

    def test_returns_gap_for_function_with_missing_lines(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        report = self._minimal_report(
            "ops.py", {"add": {"missing_lines": [3, 5]}}
        )
        json_path = self._write_json(tmp_path, report)
        gaps = parse_coverage_json(json_path, src)
        assert len(gaps) == 1
        assert gaps[0].entity_name == "add"
        assert gaps[0].uncovered_lines == (3, 5)

    def test_missing_lines_are_sorted(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        report = self._minimal_report(
            "ops.py", {"add": {"missing_lines": [9, 2, 5]}}
        )
        json_path = self._write_json(tmp_path, report)
        gaps = parse_coverage_json(json_path, src)
        assert gaps[0].uncovered_lines == (2, 5, 9)

    def test_skips_functions_with_no_missing_lines(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        report = self._minimal_report(
            "ops.py",
            {
                "add": {"missing_lines": []},
                "sub": {"missing_lines": [10]},
            },
        )
        json_path = self._write_json(tmp_path, report)
        gaps = parse_coverage_json(json_path, src)
        assert len(gaps) == 1
        assert gaps[0].entity_name == "sub"

    def test_returns_empty_when_file_not_in_report(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        report = self._minimal_report("other.py", {"foo": {"missing_lines": [1]}})
        json_path = self._write_json(tmp_path, report)
        assert parse_coverage_json(json_path, src) == ()

    def test_returns_empty_on_malformed_json(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{", encoding="utf-8")
        assert parse_coverage_json(bad, src) == ()

    def test_returns_empty_when_file_missing(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        assert parse_coverage_json(tmp_path / "nonexistent.json", src) == ()

    def test_multiple_functions_with_gaps(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        report = self._minimal_report(
            "ops.py",
            {
                "add": {"missing_lines": [3]},
                "multiply": {"missing_lines": [7, 8]},
            },
        )
        json_path = self._write_json(tmp_path, report)
        gaps = parse_coverage_json(json_path, src)
        names = {g.entity_name for g in gaps}
        assert names == {"add", "multiply"}


# ---------------------------------------------------------------------------
# ContextGatherer._gather_mypy
# ---------------------------------------------------------------------------


class TestGatherMypy:
    def _gatherer(self):
        return ContextGatherer()

    def test_returns_empty_when_mypy_exits_zero(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", return_value=_completed(returncode=0)):
            result = self._gatherer()._gather_mypy(src)
        assert result == ()

    def test_returns_error_lines_on_nonzero_exit(self, tmp_path):
        src = _make_source(tmp_path)
        stdout = "module.py:5: error: Missing return statement\nFound 1 error in 1 file\n"
        with patch("subprocess.run", return_value=_completed(stdout=stdout, returncode=1)):
            result = self._gatherer()._gather_mypy(src)
        assert len(result) == 1
        assert "Missing return statement" in result[0]

    def test_skips_non_error_lines(self, tmp_path):
        src = _make_source(tmp_path)
        stdout = "module.py:5: note: something\nmodule.py:6: error: Bad type\n"
        with patch("subprocess.run", return_value=_completed(stdout=stdout, returncode=1)):
            result = self._gatherer()._gather_mypy(src)
        assert len(result) == 1
        assert "Bad type" in result[0]

    def test_returns_empty_on_file_not_found(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = self._gatherer()._gather_mypy(src)
        assert result == ()

    def test_returns_empty_on_timeout(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("mypy", 30)):
            result = self._gatherer()._gather_mypy(src)
        assert result == ()


# ---------------------------------------------------------------------------
# ContextGatherer._gather_ruff
# ---------------------------------------------------------------------------


class TestGatherRuff:
    def _gatherer(self):
        return ContextGatherer()

    def test_returns_empty_when_no_violations(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", return_value=_completed(stdout="", returncode=0)):
            result = self._gatherer()._gather_ruff(src)
        assert result == ()

    def test_returns_violation_lines(self, tmp_path):
        src = _make_source(tmp_path)
        stdout = "module.py:1:1: F401 `os` imported but unused\nmodule.py:3:5: E501 line too long\n"
        with patch("subprocess.run", return_value=_completed(stdout=stdout, returncode=1)):
            result = self._gatherer()._gather_ruff(src)
        assert len(result) == 2
        assert any("F401" in line for line in result)

    def test_strips_blank_lines(self, tmp_path):
        src = _make_source(tmp_path)
        stdout = "module.py:1:1: F401 unused\n\n\n"
        with patch("subprocess.run", return_value=_completed(stdout=stdout)):
            result = self._gatherer()._gather_ruff(src)
        assert all(line for line in result)

    def test_returns_empty_on_file_not_found(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = self._gatherer()._gather_ruff(src)
        assert result == ()

    def test_returns_empty_on_timeout(self, tmp_path):
        src = _make_source(tmp_path)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 30)):
            result = self._gatherer()._gather_ruff(src)
        assert result == ()


# ---------------------------------------------------------------------------
# ContextGatherer._gather_coverage
# ---------------------------------------------------------------------------


class TestGatherCoverage:
    def _gatherer(self):
        return ContextGatherer()

    def test_returns_empty_when_no_test_file(self, tmp_path):
        src = _make_source(tmp_path, "orphan.py")
        # No test file exists → should short-circuit without running anything
        with patch("subprocess.run") as mock_run:
            result = self._gatherer()._gather_coverage(src)
        assert result == ()
        mock_run.assert_not_called()

    def test_calls_coverage_run_then_json(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        test = tmp_path / "test_ops.py"
        test.write_text("", encoding="utf-8")

        with patch("subprocess.run", return_value=_completed()) as mock_run, \
             patch("src.dev.test_generator.analyze.context.parse_coverage_json",
                   return_value=()):
            self._gatherer()._gather_coverage(src)

        assert mock_run.call_count == 2
        first_cmd = mock_run.call_args_list[0][0][0]
        assert "coverage" in first_cmd
        assert "run" in first_cmd
        second_cmd = mock_run.call_args_list[1][0][0]
        assert "coverage" in second_cmd
        assert "json" in second_cmd

    def test_returns_empty_on_timeout(self, tmp_path):
        src = _make_source(tmp_path, "ops.py")
        (tmp_path / "test_ops.py").write_text("", encoding="utf-8")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("coverage", 120)):
            result = self._gatherer()._gather_coverage(src)
        assert result == ()


# ---------------------------------------------------------------------------
# ContextGatherer.gather (integration of all three helpers)
# ---------------------------------------------------------------------------


class TestGather:
    def test_gather_returns_analysis_context(self, tmp_path):
        src = _make_source(tmp_path)
        g = ContextGatherer()
        with patch.object(g, "_gather_mypy", return_value=("error: foo",)), \
             patch.object(g, "_gather_ruff", return_value=("F401 unused",)), \
             patch.object(g, "_gather_coverage", return_value=()):
            ctx = g.gather(src)

        assert isinstance(ctx, AnalysisContext)
        assert ctx.mypy_issues == ("error: foo",)
        assert ctx.ruff_issues == ("F401 unused",)
        assert ctx.coverage_gaps == ()

    def test_gather_reads_source_code(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("x = 42\n", encoding="utf-8")
        g = ContextGatherer()
        with patch.object(g, "_gather_mypy", return_value=()), \
             patch.object(g, "_gather_ruff", return_value=()), \
             patch.object(g, "_gather_coverage", return_value=()):
            ctx = g.gather(src)
        assert ctx.source_code == "x = 42\n"

    def test_gather_is_frozen_value_object(self, tmp_path):
        src = _make_source(tmp_path)
        g = ContextGatherer()
        with patch.object(g, "_gather_mypy", return_value=()), \
             patch.object(g, "_gather_ruff", return_value=()), \
             patch.object(g, "_gather_coverage", return_value=()):
            ctx = g.gather(src)
        with pytest.raises((AttributeError, TypeError)):
            ctx.source_code = "mutated"  # type: ignore[misc]
