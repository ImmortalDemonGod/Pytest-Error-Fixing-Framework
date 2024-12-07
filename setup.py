from setuptools import setup, find_packages

setup(
    name='pytest_fixer',
    version='0.1.0',
    description='A framework for fixing Pytest errors',
    author='openhands',
    author_email='openhands@all-hands.dev',
    packages=find_packages(),
    install_requires=[
        'mkdocs',
    ],
)
