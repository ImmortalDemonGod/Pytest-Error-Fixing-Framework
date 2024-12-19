"""Global pytest fixtures"""
import sys
from pathlib import Path

# Add the src directory to PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "src"))

from tests.fixtures.git_fixtures import *
from tests.fixtures.integration_fixtures import *

pytest_plugins = ['plugin1', 'plugin2']
