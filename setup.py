# setup.py
from setuptools import setup, find_packages

setup(
    name="pytest_fixer",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where='src'),  # Automatically find all packages
    install_requires=[
        "mkdocs",
    ]
)
