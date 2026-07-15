import types
from unittest.mock import Mock

from branch_fixer.services.pytest.runner import PytestPlugin


def test_pytest_collection_modifyitems_emits_no_stdout(capsys):
    fake_runner = Mock()
    plugin = PytestPlugin(fake_runner)

    items = [
        types.SimpleNamespace(nodeid="a::test_one"),
        types.SimpleNamespace(nodeid="b::test_two"),
    ]

    plugin.pytest_collection_modifyitems(None, None, items)

    captured = capsys.readouterr()
    assert captured.out == ""
