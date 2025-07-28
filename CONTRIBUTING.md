# Contributing to Pytest-Fixer

First off, thank you for considering contributing to Pytest-Fixer! It's people like you that make open source such a great community.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/ImmortalDemonGod/pytest-fixer/issues/new)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

### Fork & create a branch

If you're ready to contribute, fork the repository and create a new branch from `main`:

```sh
git checkout -b my-new-feature
```

### Get the code running

This project uses `uv` for environment and dependency management. To get started:

1.  **Create the virtual environment:**
    ```sh
    uv venv
    ```
2.  **Install dependencies:**
    ```sh
    uv sync
    ```

### Make your changes

Make your changes to the code. Ensure that your code follows the existing style to maintain consistency.

### Run the tests

Before submitting your changes, please run the full test suite to ensure that everything is still working correctly.

```sh
pytest
```

### Commit and Push

Commit your changes with a clear and descriptive message, then push your branch to your fork:

```sh
git commit -m "feat: Add some amazing feature"
git push origin my-new-feature
```

### Submit a Pull Request

Go to the repository on GitHub and open a pull request. Provide a clear description of the changes you've made.

Thank you for your contribution!
