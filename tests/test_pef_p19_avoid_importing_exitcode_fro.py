# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
import inspect
import sys

from src.branch_fixer.services.pytest.models import SessionResult  # verified working import — do not edit


def test_sessionresult_pins_the_finding_defect():
    # The finding: models.py imports ExitCode from the *private* _pytest.main
    # module instead of the public `pytest` package. Since `pytest.ExitCode`
    # and `_pytest.main.ExitCode` are the same object, a type check can't
    # distinguish them — the defect is which module the import statement
    # names, so we inspect the defining module's source directly.
    module = sys.modules[SessionResult.__module__]
    source = inspect.getsource(module)
    assert "_pytest" not in source, (
        "SessionResult's defining module must not reference the private "
        "_pytest package (e.g. `from _pytest.main import ExitCode`); it "
        "should import ExitCode from the public `pytest` package instead"
    )
