# System Architecture

This document provides the canonical overview of the `pytest-fixer` system architecture. It is designed as the single source of truth for contributors, aligning with **Domain-Driven Design (DDD)** and **Clean Architecture** principles to create a maintainable, scalable, and understandable system.

---

## 1. Core Architectural Principles

The system is organized into a layered architecture to ensure a clear separation of concerns. This design prevents tight coupling between business logic and technical implementation, making the system easier to test and evolve.

1.  **Domain Layer (`src/branch_fixer/core/`)**: Contains the core business logic, rules, and types. This layer is the heart of the application and is completely independent of any external frameworks or technologies (like databases, APIs, or the file system).
2.  **Application Layer (`src/branch_fixer/orchestration/`)**: Orchestrates the use cases of the application. It coordinates the domain objects and infrastructure services to perform tasks required by the user, such as "fix this list of failing tests."
3.  **Infrastructure Layer (`src/branch_fixer/services/`)**: Implements all external-facing concerns. This includes integrations with `pytest`, `Git`, LLM APIs, and the file system. It provides the concrete "how" for the abstract "what" defined by the higher layers.

---

## 2. Component Breakdown by Layer

### **Domain Layer (`core`)**

-   **`models.py`**: Defines the core concepts of our domain as data structures.
    -   **`TestError` (Aggregate Root):** Represents a single failing test. It is the main entity that the system operates on, encapsulating its state (`status`), details (`error_details`), and history (`fix_attempts`).
    -   **`FixAttempt` (Entity):** A record of a single attempt by the AI to fix a `TestError`, tracking the `temperature` used and its `status` (success/failed).
    -   **`ErrorDetails` (Value Object):** An immutable object that holds the specific details of a failure (type, message, stack trace).
    -   **`CodeChanges` (Value Object):** An immutable representation of the code modification suggested by the AI.

### **Application Layer (`orchestration`)**

-   **`FixService`**: The primary application service for the use case of "attempt to fix a single error." It contains the retry logic, temperature scaling, and coordinates the necessary infrastructure services to achieve this.
-   **`FixOrchestrator`**: Manages the higher-level use case of "run a full fix session for multiple errors." It tracks the overall state of the session via the `FixSession` model.
-   **`FixSession` (Application Model):** A data class that tracks the state of an end-to-end run, including the list of errors, progress, and final status (`COMPLETED`, `FAILED`).

### **Infrastructure Layer (`services`)**

-   **`services/ai/manager.py` (`AIManager`):** Encapsulates all communication with Large Language Models. It uses `litellm` for provider flexibility, constructs detailed prompts from `TestError` objects, and parses structured `CodeChanges` from the LLM's response.
-   **`services/pytest/runner.py` (`PytestRunner`):** The system's interface to `pytest`. It programmatically invokes `pytest`, using a custom plugin to capture highly detailed, structured results (`SessionResult`, `TestResult`) rather than relying on brittle text parsing.
-   **`services/pytest/parsers/`**: A suite of parsers that can translate raw `pytest` text output into structured `ErrorInfo` objects. This serves as a fallback or alternative to the plugin-based capture.
-   **`services/git/repository.py` (`GitRepository` & `BranchManager`):** Provides a high-level API for all Git operations. It handles the creation of isolated fix branches, committing changes, and cleaning up, ensuring the user's main branch is never directly modified.
-   **`services/code/change_applier.py` (`ChangeApplier`):** A critical safety component responsible for all file system writes. It automatically creates a backup of any file before modification and can reliably restore it if the verification step fails.
-   **`storage/`**: Contains persistence logic. The `SessionStore` uses `TinyDB` to save `FixSession` data to a local JSON file for auditing and future resumption capabilities.

---

## 3. End-to-End Workflow: Data Flow

The diagram below illustrates the flow of control and data during a typical `fix` command execution.

```mermaid
graph TD
    A[CLI: `fix` command] --> B{PytestRunner: `run_test()`};
    B --> C{Parse Failures};
    C --> D[FixOrchestrator: `start_session(errors)`];
    D --> E[For each `TestError`];
    E --> F{BranchManager: `create_fix_branch()`};
    F --> G{AIManager: `generate_fix()`};
    G --> H{ChangeApplier: `apply_changes_with_backup()`};
    H --> I{PytestRunner: `verify_fix()`};
    I -- Success --> J[Mark `TestError` as Fixed];
    I -- Failure --> K{Restore from Backup & Retry};
    K --> G;
    J --> E;
    E --> L[Session `COMPLETED`];
    L --> M{Cleanup Branches};

    subgraph "Application Layer"
        D
        E
    end

    subgraph "Infrastructure Layer"
        B
        F
        G
        H
        I
        M
    end
```

This structured, layered design ensures that the core logic of fixing a test is decoupled from the specific tools used to accomplish it, making the system robust, testable, and extensible.