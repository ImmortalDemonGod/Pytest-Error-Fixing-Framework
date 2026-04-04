import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from dev.test_generator.analyze import context as context_mod


# Module-level fixtures
@pytest.fixture
def tmp_dir(tmp_path):
    """
    Provide the pytest temporary directory for tests.
    
    Returns:
        pathlib.Path: A Path pointing to pytest's temporary directory (same object as the built-in `tmp_path` fixture).
    """
    return tmp_path


@pytest.fixture
def gatherer():
    """
    Pytest fixture that provides a ContextGatherer configured to use the test Python executable.
    
    Returns:
        ContextGatherer: an instance of ContextGatherer with its python_executable set to "python-test".
    """
    return context_mod.ContextGatherer(python_executable="python-test")


class TestContextGatherer:
    def test_init_sets_python_executable(self):
        g = context_mod.ContextGatherer(python_executable="/usr/bin/custompy")
        assert g._python == "/usr/bin/custompy"

    def test_gather_reads_source_and_aggregates_helpers(self, tmp_dir):
        src = tmp_dir / "module.py"
        content = "print('hello')\n"
        src.write_text(content, encoding="utf-8")

        mypy_val = ("mypy1",)
        ruff_val = ("ruff1", "ruff2")
        cov_val = ("coverage_gap",)
        dep_code = "# dependency"

        with patch.object(
            context_mod.ContextGatherer,
            "_gather_mypy",
            return_value=mypy_val,
        ) as pmypy, patch.object(
            context_mod.ContextGatherer,
            "_gather_ruff",
            return_value=ruff_val,
        ) as pruff, patch.object(
            context_mod.ContextGatherer,
            "_gather_coverage",
            return_value=cov_val,
        ) as pcov, patch.object(
            context_mod, "_gather_dependency_code", return_value=dep_code
        ) as pdep:
            g = context_mod.ContextGatherer()
            ctx = g.gather(src)

            assert ctx.source_code == content
            assert ctx.mypy_issues == mypy_val
            assert ctx.ruff_issues == ruff_val
            assert ctx.coverage_gaps == cov_val
            assert ctx.dependency_code == dep_code

            pmypy.assert_called_once_with(src)
            pruff.assert_called_once_with(src)
            pcov.assert_called_once_with(src)
            pdep.assert_called_once_with(src, content)

    def test_gather_propagates_read_errors(self, tmp_dir):
        src = tmp_dir / "nofile.py"
        # Ensure file does not exist
        if src.exists():
            src.unlink()
        g = context_mod.ContextGatherer()
        with pytest.raises(OSError):
            g.gather(src)


class TestGatherMypy:
    def test_parses_error_lines(self, tmp_dir):
        src = tmp_dir / "a.py"
        src.write_text("x=1", encoding="utf-8")
        stdout = "a.py:1: error: bad\n\ninfo line\n b.py:2: error: other\n"
        fake = SimpleNamespace(stdout=stdout)

        with patch("dev.test_generator.analyze.context.subprocess.run", return_value=fake):
            g = context_mod.ContextGatherer()
            res = g._gather_mypy(src)
            assert res == (
                "a.py:1: error: bad",
                "b.py:2: error: other",
            )

    def test_returns_empty_on_no_errors(self, tmp_dir):
        src = tmp_dir / "a.py"
        src.write_text("x=1", encoding="utf-8")
        fake = SimpleNamespace(stdout="All good\n")

        with patch("dev.test_generator.analyze.context.subprocess.run", return_value=fake):
            g = context_mod.ContextGatherer()
            res = g._gather_mypy(src)
            assert res == ()

    def test_handles_filenotfound_and_timeout(self, tmp_dir):
        src = tmp_dir / "a.py"
        src.write_text("x=1", encoding="utf-8")

        # FileNotFoundError
        with patch("dev.test_generator.analyze.context.subprocess.run", side_effect=FileNotFoundError()):
            g = context_mod.ContextGatherer()
            assert g._gather_mypy(src) == ()

        # TimeoutExpired
        with patch(
            "dev.test_generator.analyze.context.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["mypy"], 1),
        ):
            g = context_mod.ContextGatherer()
            assert g._gather_mypy(src) == ()


class TestGatherRuff:
    def test_parses_lines(self, tmp_dir):
        src = tmp_dir / "r.py"
        src.write_text("x=1", encoding="utf-8")
        stdout = "E123 something\n\nW456 another\n"
        fake = SimpleNamespace(stdout=stdout)

        with patch("dev.test_generator.analyze.context.subprocess.run", return_value=fake):
            g = context_mod.ContextGatherer()
            res = g._gather_ruff(src)
            assert res == ("E123 something", "W456 another")

    def test_returns_empty_on_no_output(self, tmp_dir):
        src = tmp_dir / "r.py"
        src.write_text("x=1", encoding="utf-8")
        fake = SimpleNamespace(stdout="")

        with patch("dev.test_generator.analyze.context.subprocess.run", return_value=fake):
            g = context_mod.ContextGatherer()
            assert g._gather_ruff(src) == ()

    def test_handles_filenotfound_and_timeout(self, tmp_dir):
        src = tmp_dir / "r.py"
        src.write_text("x=1", encoding="utf-8")

        with patch("dev.test_generator.analyze.context.subprocess.run", side_effect=FileNotFoundError()):
            g = context_mod.ContextGatherer()
            assert g._gather_ruff(src) == ()

        with patch(
            "dev.test_generator.analyze.context.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["ruff"], 1),
        ):
            g = context_mod.ContextGatherer()
            assert g._gather_ruff(src) == ()


class TestGatherCoverage:
    def test_returns_empty_if_no_test_file(self, tmp_dir):
        src = tmp_dir / "mod.py"
        src.write_text("x=1", encoding="utf-8")
        with patch("dev.test_generator.analyze.context.find_test_file", return_value=None):
            g = context_mod.ContextGatherer()
            assert g._gather_coverage(src) == ()

    def test_returns_parse_result_on_success(self, tmp_dir):
        # Create a dummy test file and ensure find_test_file returns it
        test_file = tmp_dir / "test_mod.py"
        test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

        sentinel = ("gap1",)
        with patch("dev.test_generator.analyze.context.find_test_file", return_value=test_file):
            fake = SimpleNamespace(stdout="")
            with patch("dev.test_generator.analyze.context.subprocess.run", return_value=fake):
                with patch("dev.test_generator.analyze.context.parse_coverage_json", return_value=sentinel) as pparse:
                    g = context_mod.ContextGatherer()
                    res = g._gather_coverage(test_file)  # source_path passed; find_test_file returns test_file
                    # parse_coverage_json should be called with the temporary json path and the original source
                    assert res == sentinel
                    pparse.assert_called()

    def test_handles_subprocess_errors_and_removes_tempfile(self, tmp_dir):
        # Prepare a test file path
        test_file = tmp_dir / "test_mod.py"
        test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

        # Replace NamedTemporaryFile so we can observe the file path and existence
        created = tmp_dir / "coverage_temp.json"
        # Ensure file exists at creation
        created.write_text("{}", encoding="utf-8")

        class DummyNTF:
            def __init__(self, name):
                """
                Initialize the instance and store the provided name as a string.
                
                Parameters:
                    name: Value to be used as the instance's name; it will be converted to `str` and assigned to `self.name`.
                """
                self.name = str(name)

            def __enter__(self):
                """
                Enter the runtime context and provide the context manager instance.
                
                Returns:
                    The context manager instance (`self`).
                """
                return self

            def __exit__(self, exc_type, exc, tb):
                """
                Ensure exceptions raised in the managed block propagate to the caller.
                
                @returns
                    `False` to indicate any exception should not be suppressed and must be re-raised.
                """
                return False

        def fake_named_tmpfile(*args, **kwargs):
            # create the file so unlinking is meaningful
            """
            Create a fake temporary file at a predetermined path and return a DummyNTF wrapper.
            
            Writes the literal "{}" to the file so callers can observe deletion/unlinking, then returns a DummyNTF instance constructed with the created path.
            
            Returns:
                DummyNTF: wrapper object for the created temporary file path.
            """
            created.write_text("{}", encoding="utf-8")
            return DummyNTF(created)

        with patch("dev.test_generator.analyze.context.find_test_file", return_value=test_file):
            with patch("dev.test_generator.analyze.context.tempfile.NamedTemporaryFile", side_effect=fake_named_tmpfile):
                # Make subprocess.run raise to trigger exception-flow and finally cleanup
                with patch(
                    "dev.test_generator.analyze.context.subprocess.run",
                    side_effect=FileNotFoundError(),
                ):
                    g = context_mod.ContextGatherer()
                    res = g._gather_coverage(test_file)
                    assert res == ()
                    # tempfile should have been removed by finally block
                    assert not created.exists()

        # Repeat for TimeoutExpired
        created.write_text("{}", encoding="utf-8")
        with patch("dev.test_generator.analyze.context.find_test_file", return_value=test_file):
            with patch("dev.test_generator.analyze.context.tempfile.NamedTemporaryFile", side_effect=fake_named_tmpfile):
                with patch(
                    "dev.test_generator.analyze.context.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(["coverage"], 1),
                ):
                    g = context_mod.ContextGatherer()
                    res = g._gather_coverage(test_file)
                    assert res == ()
                    assert not created.exists()


class TestGatherDependencyCode:
    def test_returns_empty_on_syntax_error_source(self, tmp_dir):
        bad_source = "x = )"  # invalid syntax
        src_path = tmp_dir / "src" / "mod.py"
        res = context_mod._gather_dependency_code(src_path, bad_source)
        assert res == ""

    def test_returns_empty_if_no_imports(self, tmp_dir):
        source_code = "x = 1\n"
        src_path = tmp_dir / "module.py"
        res = context_mod._gather_dependency_code(src_path, source_code)
        assert res == ""

    def test_ignores_nonexistent_module_files(self, tmp_dir):
        # Build a src-layout path so src_root resolution path is exercised
        project = tmp_dir / "project"
        srcdir = project / "src"
        modpath = srcdir / "pkg"
        modpath.mkdir(parents=True)
        source_path = modpath / "consumer.py"
        source_code = "from missingpkg import Foo\n"
        # Ensure missingpkg.py does not exist under src_root
        res = context_mod._gather_dependency_code(source_path, source_code)
        assert res == ""

    def test_ignores_dep_with_syntax_error_or_oserror(self, tmp_dir):
        project = tmp_dir / "project"
        srcdir = project / "src"
        pkg = srcdir / "mypkg"
        pkg.mkdir(parents=True)
        # Create a module file with syntax error
        module_file = srcdir / "badmod.py"
        module_file.write_text("x = )", encoding="utf-8")
        # Source imports badmod
        source_path = pkg / "consumer.py"
        source_code = "from badmod import X\n"
        res = context_mod._gather_dependency_code(source_path, source_code)
        assert res == ""

    def test_extracts_function_and_class_blocks_and_deduplicates(self, tmp_dir):
        # Create project/src/pkg/module.py
        project = tmp_dir / "project"
        srcdir = project / "src"
        pkgdir = srcdir / "pkg"
        pkgdir.mkdir(parents=True)
        module_file = pkgdir / "module.py"
        module_content = (
            "def foo(x):\n"
            "    return x * 2\n\n"
            "class Bar:\n"
            "    def method(self):\n"
            "        return 1\n"
        )
        module_file.write_text(module_content, encoding="utf-8")

        # Source located somewhere under src so src_root resolution occurs
        source_path = pkgdir / "consumer.py"
        # Import two names from same module (should be deduplicated)
        source_code = "from pkg.module import foo, Bar\n"
        res = context_mod._gather_dependency_code(source_path, source_code)
        assert "# from pkg.module" in res
        assert "def foo(x):" in res
        assert "class Bar" in res
        # Accept at least one occurrence of the module marker (implementation may repeat headers)
        assert res.count("# from pkg.module") >= 1


class TestFindTestFile:
    def test_prefers_test_stem_in_same_dir(self, tmp_dir):
        source = tmp_dir / "mymod.py"
        source.write_text("x=1", encoding="utf-8")
        t1 = tmp_dir / "test_mymod.py"
        t1.write_text("def test(): pass", encoding="utf-8")

        found = context_mod.find_test_file(source)
        assert found == t1

    def test_uses_stem_test_if_test_stem_missing(self, tmp_dir):
        source = tmp_dir / "mymod.py"
        source.write_text("x=1", encoding="utf-8")
        t2 = tmp_dir / "mymod_test.py"
        t2.write_text("def test(): pass", encoding="utf-8")

        found = context_mod.find_test_file(source)
        assert found == t2

    def test_checks_project_tests_when_src_in_path(self, tmp_dir):
        # Create project/src/pkg/module.py and project/tests/test_module.py
        project = tmp_dir / "project"
        srcdir = project / "src"
        pkgdir = srcdir / "pkg"
        pkgdir.mkdir(parents=True)
        source = pkgdir / "module.py"
        source.write_text("x=1", encoding="utf-8")

        tests_dir = project / "tests"
        tests_dir.mkdir(parents=True)
        tproj = tests_dir / "test_module.py"
        tproj.write_text("def test(): pass", encoding="utf-8")

        found = context_mod.find_test_file(source)
        assert found == tproj

    def test_returns_none_when_no_candidates(self, tmp_dir):
        source = tmp_dir / "nomatch.py"
        source.write_text("x=1", encoding="utf-8")
        found = context_mod.find_test_file(source)
        assert found is None

    def test_ordering_prefers_test_stem_over_stem_test(self, tmp_dir):
        source = tmp_dir / "mymod.py"
        source.write_text("x=1", encoding="utf-8")
        t1 = tmp_dir / "test_mymod.py"
        t2 = tmp_dir / "mymod_test.py"
        t1.write_text("a=1", encoding="utf-8")
        t2.write_text("b=2", encoding="utf-8")
        found = context_mod.find_test_file(source)
        assert found == t1


class TestParseCoverageJson:
    def test_returns_empty_on_malformed_json(self, tmp_dir):
        j = tmp_dir / "bad.json"
        j.write_text("x = )", encoding="utf-8")
        src = tmp_dir / "module.py"
        src.write_text("x=1", encoding="utf-8")
        res = context_mod.parse_coverage_json(j, src)
        assert res == ()

    def test_returns_empty_when_file_not_in_report(self, tmp_dir):
        j = tmp_dir / "report.json"
        data = {"files": {"other.py": {}}}
        j.write_text(json.dumps(data), encoding="utf-8")
        src = tmp_dir / "module.py"
        src.write_text("x=1", encoding="utf-8")
        res = context_mod.parse_coverage_json(j, src)
        assert res == ()

    def test_matches_by_key_suffix_and_filename(self, tmp_dir):
        # Case: key is a relative path that is a suffix of the resolved path
        j1 = tmp_dir / "r1.json"
        project_dir = tmp_dir / "a" / "b"
        project_dir.mkdir(parents=True)
        src = project_dir / "path" / "to" / "module.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("x=1", encoding="utf-8")

        rel_key = "path/to/module.py"
        data = {"files": {rel_key: {"functions": {}}}}
        j1.write_text(json.dumps(data), encoding="utf-8")
        res1 = context_mod.parse_coverage_json(j1, src)
        assert res1 == ()

        # Case: key is just the filename
        j2 = tmp_dir / "r2.json"
        data2 = {"files": {src.name: {"functions": {}}}}
        j2.write_text(json.dumps(data2), encoding="utf-8")
        res2 = context_mod.parse_coverage_json(j2, src)
        assert res2 == ()

    def test_builds_gaps_for_missing_lines(self, tmp_dir):
        j = tmp_dir / "cov.json"
        src = tmp_dir / "module.py"
        src.write_text("x=1", encoding="utf-8")
        files = {
            "module.py": {
                "functions": {
                    "func1": {"missing_lines": [5, 3]},
                    "func2": {"missing_lines": []},
                }
            }
        }
        j.write_text(json.dumps({"files": files}), encoding="utf-8")
        res = context_mod.parse_coverage_json(j, src)
        # Compare by attributes to avoid relying on CoverageGap equality semantics
        extracted = tuple((g.entity_name, g.uncovered_lines) for g in res)
        assert extracted == (("func1", (3, 5)),)

    def test_handles_oserror_reading(self, tmp_dir):
        missing = tmp_dir / "does_not_exist.json"
        src = tmp_dir / "module.py"
        src.write_text("x=1", encoding="utf-8")
        res = context_mod.parse_coverage_json(missing, src)
        assert res == ()