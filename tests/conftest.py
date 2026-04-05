"""Global pytest fixtures"""

pytest_plugins = [
    "pytest_asyncio",
    "tests.fixtures.git_fixtures",
    "tests.fixtures.integration_fixtures",
]
