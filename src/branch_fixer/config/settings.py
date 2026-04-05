# branch_fixer/config/settings.py
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = os.environ.get("BRANCH_FIXER_DEBUG", "").lower() in ("1", "true", "yes")
SECRET_KEY = os.environ.get("BRANCH_FIXER_SECRET_KEY", "")
