# RED test for the finding — import verified by the harness; expected value from the finding's own command (see FACT).
from src.branch_fixer.config.logging_config import setup_logging  # verified working import — do not edit

import logging


def test_setup_logging_pins_the_finding_defect():
    snoop_logger = logging.getLogger("snoop")
    for h in list(snoop_logger.handlers):
        snoop_logger.removeHandler(h)
        h.close()

    setup_logging()
    a = len(snoop_logger.handlers)

    setup_logging()
    b = len(snoop_logger.handlers)

    assert a == b, (a, b)
