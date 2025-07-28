# Welcome to Pytest Fixer

`pytest-fixer` is an AI-powered tool that automatically identifies, analyzes, and fixes failing `pytest` tests in your Python projects. It integrates directly into a developer's workflow, using a sophisticated engine to parse test failures, query large language models for solutions, and verify fixes within a safe, Git-based environment.

This documentation is designed to help you get the most out of the tool, whether you are a first-time user looking to get started, a seasoned contributor wanting to dive into the code, or a researcher interested in the underlying technology.

---

## Getting Started

New to `pytest-fixer`? Start here to get the tool up and running in minutes.

-   **[Installation and Setup](./user-guide/01-installation.md)**: A step-by-step guide to installing the tool and its dependencies.
-   **[Quick Start Guide](./user-guide/02-quickstart.md)**: Your first five minutes to a working fix.
-   **[CLI Reference](./user-guide/03-cli-reference.md)**: A complete guide to the command-line options and interactive mode.

---

## For Developers and Contributors

Ready to dive into the code? These guides provide everything you need to know to contribute to the project.

-   **[System Architecture](./developer-guide/01-architecture.md)**: A deep dive into the design and architecture of the system.
-   **[Contribution Guide](./developer-guide/02-contribution-guide.md)**: The process for contributing code, documentation, and bug reports.
-   **[Testing Strategy](./developer-guide/03-testing-strategy.md)**: An overview of the project's own testing philosophy and practices.

---

## Design and Research

Explore the advanced features and research behind `pytest-fixer`.

-   **[Strategic Analysis](./design-and-research/01-strategic-analysis.md)**: The strategic and technical assessment that led to this project.
-   **[SWE-bench Strategy](./design-and-research/02-swe-bench-strategy.md)**: Our approach to the Software Engineering Benchmark for automated program repair.
-   **[Git API Design](./design-and-research/03-git-api-design.md)**: The design for a robust Git API.

---

## Reference Library

Background reading and conceptual knowledge that informs the project.

-   **[DDD Principles](./reference/ddd-principles.md)**: The core concepts of Domain-Driven Design used in the project.
-   **[Our Debugging Philosophy](./reference/debugging-workflow.md)**: The systematic approach to debugging that guides our tool's design.
-   **[Bug Taxonomy](./reference/bug-taxonomy.md)**: How we classify and think about software defects.
-   **[Hypothesis Guide](./reference/hypothesis-guide.md)**: A practical guide to property-based testing with Hypothesis.