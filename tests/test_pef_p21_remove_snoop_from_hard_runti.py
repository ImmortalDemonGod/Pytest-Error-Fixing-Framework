from unittest.mock import patch

from branch_fixer.utils.workspace import WorkspaceValidator


def test_check_dependencies_snoop_optional():
    """snoop must not be a hard runtime dependency (F63)."""
    assert "snoop" not in WorkspaceValidator.REQUIRED_DEPENDENCIES

    def mock_import(name, *args, **kwargs):
        if name == "snoop":
            raise ImportError("No module named 'snoop'")
        return object()

    with patch("importlib.import_module", side_effect=mock_import):
        # Should not raise even though snoop is unimportable.
        WorkspaceValidator.check_dependencies()
