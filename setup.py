# setup.py
from setuptools import setup, find_namespace_packages

setup(
    name="pytest_fixer",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    install_requires=[
        "mkdocs",  # keeping your existing dependencies
    ]
)