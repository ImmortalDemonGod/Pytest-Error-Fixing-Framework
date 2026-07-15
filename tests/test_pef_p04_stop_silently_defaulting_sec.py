# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.config.settings import SECRET_KEY  # verified working import — do not edit


def test_secret_key_pins_the_finding_defect():
    # F53: with BRANCH_FIXER_SECRET_KEY unset in this test's environment, settings.py
    # currently defaults SECRET_KEY to "" (os.environ.get(..., "")). An empty-string
    # secret is cryptographically useless and must never be silently accepted -
    # the correct behavior is that SECRET_KEY is never None/"" once the module has
    # loaded (it should have raised or been substituted with a real generated value).
    assert SECRET_KEY not in (None, ""), (
        "SECRET_KEY must not silently default to an empty string when "
        "BRANCH_FIXER_SECRET_KEY is unset"
    )
