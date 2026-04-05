# Installation and Setup

This guide will walk you through the steps required to install and configure `pytest-fixer`.

---

## Requirements

Before you begin, ensure you have the following installed on your system:

-   Python 3.13+
-   Git
-   An active API Key for an LLM provider via [OpenRouter](https://openrouter.ai)

---

## Installation Steps

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/ImmortalDemonGod/Pytest-Error-Fixing-Framework.git
    cd Pytest-Error-Fixing-Framework
    ```

2.  **Set Up the Virtual Environment**

    ```bash
    python3.13 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**

    ```bash
    pip install -e .
    ```

---

## Configuration

The tool requires an OpenRouter API key to communicate with a Large Language Model.

1.  **Create a `.env` file** in the root of the project directory.

2.  **Add your API key** to the `.env` file:

    ```env
    OPENROUTER_API_KEY=sk-or-v1-...
    ```

3.  **Load the environment** before running the tool:

    ```bash
    set -a && source .env && set +a
    ```

The tool is now installed and configured. You are ready to run your first fix!
