# Reference: Domain-Driven Design (DDD) Principles

This document provides a reference for the core concepts of Domain-Driven Design (DDD) that inform the architecture of the `pytest-fixer` project. These principles help in building a robust, maintainable, and scalable system by aligning the software design with the business domain.

---

## Core DDD Concepts

### 1. Ubiquitous Language

A shared, rigorous language between developers and domain experts. This language is used in all forms of communication, including code, to eliminate ambiguity and ensure that the software model accurately reflects the domain.

**In `pytest-fixer`:** Terms like `TestError`, `FixAttempt`, `FixSession`, and `GenerationStrategy` are part of the ubiquitous language.

### 2. Bounded Contexts

A boundary within which a particular domain model is defined and applicable. Each bounded context has its own ubiquitous language and model. This helps to manage complexity by breaking down a large system into smaller, more manageable parts.

**In `pytest-fixer`:** We have two primary bounded contexts:
-   **Test Generation Context**: Responsible for creating new tests.
-   **Branch Fixing Context**: Responsible for fixing failing tests.

### 3. Aggregates

A cluster of associated objects that are treated as a single unit for the purpose of data changes. An aggregate has a root entity, known as the **Aggregate Root**, which is the only member of the aggregate that outside objects are allowed to hold references to. This ensures the consistency and integrity of the objects within the aggregate.

### 4. Entities

Objects that have a distinct identity that runs through time and different states. They are not defined by their attributes, but rather by their thread of continuity and identity.

### 5. Value Objects

Objects that describe a characteristic or an attribute of a domain, but have no conceptual identity. They are immutable and are defined by their attributes. Two value objects with the same attributes are considered equal.

### 6. Domain Services

Operations that don't naturally fit within an entity or value object. They represent a stateless operation within the domain layer that acts on domain objects.

### 7. Repositories

Mediates between the domain and data mapping layers, providing a collection-like interface for accessing domain objects. They encapsulate the logic required to obtain object references and persist changes.

### 8. Domain Events

A record of something that happened in the domain. They are used to communicate changes between different parts of the system, often across bounded contexts, in a decoupled manner.