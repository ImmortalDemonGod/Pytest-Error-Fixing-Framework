# Bug catalog — pef-p20-make-setup-logging-idempoten

| # | Location | Defect | Evidence (harness-executed) | Caught by |
|---|----------|--------|------------------------------|-----------|
| 1 | src/branch_fixer/config/logging_config.py:30-37 | setup_logging() adds a new FileHandler to the 'snoop' logger (lines 31-37) without checking whether handlers already exist. The root logger's handlers are replaced by basicConfig(force=True), but the snoop-specific logger is not cleared. Every subsequent call to setup_logging() appends another duplicate FileHandler to the snoop logger, leading to duplicated log entries. setup_logging() is called twice in the normal run path: once in main.py:11 and again inside fix() at run_cli.py:94. | .venv/bin/python -c "import logging; from branch_fixer.config.logging_config import setup_logging; setup_logging(); a=len(logging.getLogger('snoop').handlers); setup_logging(); b=len(logging.getLogger('snoop').handlers); assert a==b, (a,b)" exits 0 (calling setup_logging twice adds no duplicate snoop FileHandler). | `tests/test_pef_p20_make_setup_logging_idempoten.py` |

- **Expected (per the finding goal):** .venv/bin/python -c "import logging; from branch_fixer.config.logging_config import setup_logging; setup_logging(); a=len(logging.getLogger('snoop').handlers); setup_logging(); b=len(logging.getLogger('snoop').handlers); assert a==b, (a,b)" exits 0 (calling setup_logging twice adds no duplicate snoop FileHandler).
- Every row above is recorded ground truth (finding fields + harness-executed command outputs); no value is estimated.
