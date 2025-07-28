# Installation and Setup

This guide will walk you through the steps required to install and configure `pytest-fixer`.

---

## Requirements

Before you begin, ensure you have the following installed on your system:

-   Python 3.13+
-   Git
-   `uv` (for environment management, recommended)
-   An active API Key for an LLM provider (e.g., OpenAI, Anthropic)

---

## Installation Steps

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework.git
    cd Pytest-Error-Fixing-Framework
    ```

2.  **Set Up the Virtual Environment**

    This project uses `uv` for fast and reliable dependency management.

    ```bash
    # Create the virtual environment
    uv venv

    # Activate the environment
    source .venv/bin/activate
    ```

3.  **Install Dependencies**

    Install all required packages from the lock file.

    ```bash
    uv sync
    ```

---

## Configuration

The tool requires an API key to communicate with a Large Language Model.

1.  **Create a `.env` file** in the root of the project directory. This file will securely store your API key.

2.  **Add your API key** to the `.env` file. For example, if using OpenAI:

    ```env
    # Your OpenAI API Key
    OPENAI_API_KEY="sk-..."
    ```

The tool is now installed and configured. You are ready to run your first fix!