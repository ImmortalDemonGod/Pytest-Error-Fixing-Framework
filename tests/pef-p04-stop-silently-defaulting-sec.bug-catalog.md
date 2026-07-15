# Bug catalog — pef-p04-stop-silently-defaulting-sec

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/config/settings.py:6 | `SECRET_KEY = os.environ.get("BRANCH_FIXER_SECRET_KEY", "")` defaults to an empty string when the environment variable is absent. An empty-string secret key is cryptographically useless and cannot provide any HMAC or token security guarantees. Any code relying on this key silently degrades to zero security with no error raised. | Importing branch_fixer.config.settings with BRANCH_FIXER_SECRET_KEY unset emits a warning or raises (assert via warnings.catch_warnings / pytest.raises), and no code path consumes an empty-string secret (assert settings.SECRET_KEY not in (None, '')); .venv/bin/python -m pytest -k 'settings and secret' -q exits 0. | `tests/test_pef_p04_stop_silently_defaulting_sec.py` |

- **Expected (per the finding goal):** Importing branch_fixer.config.settings with BRANCH_FIXER_SECRET_KEY unset emits a warning or raises (assert via warnings.catch_warnings / pytest.raises), and no code path consumes an empty-string secret (assert settings.SECRET_KEY not in (None, '')); .venv/bin/python -m pytest -k 'settings and secret' -q exits 0.
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
