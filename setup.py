# setup.py
from setuptools import setup, find_packages

setup(
    name="pytest_fixer",
    version="0.1.0",
    package_dir={"": "src"},
    packages=['branch_fixer', 'branch_fixer.domain', 'cli', 'shared', 'test_generator'],  # Explicitly list packages
    install_requires=[
        "mkdocs",
    ]
)