# Katana AI: Architecture & Decomposition Plan (Genesis Protocol)

## 1.0 Introduction

This document outlines the proposed architecture and phased implementation plan for the Katana AI ecosystem, as mandated by the "Genesis Directive". The objective is to evolve the existing Katana framework into a global platform for symbiotic collaboration between human specialists and artificial intelligence, thereby creating the most effective talent and project management system in history.

This plan details the design and decomposition of the four core subsystems: **Oracle**, **Agora**, **Hephaestus**, and **Athena**. It builds upon the existing agent-based orchestration logic found in the `src` directory, transforming it into a scalable, intelligent, and self-learning system.

## 2.0 Core Architecture

The Katana ecosystem will be architected as a modular, service-oriented system with Katana's core intelligence at the center. The four subsystems will function as integrated services that manage the lifecycle of tasks, specialists, code, and knowledge.

### 2.1 High-Level Diagram (Conceptual)

```mermaid
graph TD
    subgraph Katana Core
        A[Agora - Task Marketplace]
        O[Oracle - Profiling & Assignment]
        H[Hephaestus - CI/CD/CQ Pipeline]
        AT[Athena - Knowledge & Learning]
    end

    subgraph Legion (100,000 Specialists)
        Dev1[Developer 1]
        Dev2[Developer 2]
        DevN[Developer N]
    end

    subgraph External Systems
        GH[GitHub / GitLab]
        CI[CI/CD Infrastructure]
        KB[Knowledge Base]
    end

    Katana_Core_AI[Katana AI Core]

    Katana_Core_AI -- Manages --> A
    Katana_Core_AI -- Manages --> O
    Katana_Core_AI -- Manages --> H
    Katana_Core_AI -- Manages --> AT

    Dev1 -- Interacts with --> A
    Dev2 -- Interacts with --> A
    DevN -- Interacts with --> A

    A -- Distributes Tasks --> Dev1
    A -- Distributes Tasks --> Dev2
    A -- Distributes Tasks --> DevN

    O -- Provides Profiles --> A
    O -- Analyzes --> Dev1
    O -- Analyzes --> Dev2
    O -- Analyzes --> DevN
    O -- Ingests Data from --> GH

    Dev1 -- Submits PRs --> H
    Dev2 -- Submits PRs --> H
    DevN -- Submits PRs --> H

    H -- Runs AI Code Review --> Katana_Core_AI
    H -- Deploys to --> CI
    H -- Feeds Data to --> AT

    AT -- Provides Insights --> Katana_Core_AI
    AT -- Generates Learning --> Dev1
    AT -- Generates Learning --> Dev2
    AT -- Generates Learning --> DevN
    AT -- Updates --> KB
```

### 2.2 Component Descriptions

#### 2.2.1 "Agora" — Dynamic Task Marketplace
*   **Purpose:** To serve as the central, decentralized exchange for all tasks within the ecosystem.
*   **Evolution:** This system will be evolved from the current `TaskOrchestrator`. The in-memory `task_queue` will be replaced by a robust, persistent database managed by the `DAO` layer.
*   **Features:**
    *   **Task Ledger:** A database of all available, in-progress, and completed tasks.
    *   **Dynamic Valuation:** Tasks will be assigned a value (e.g., in "Sapiens Coin") based on complexity, urgency, and demand.
    *   **Bidding/Claiming:** Specialists can bid on tasks or claim them directly based on their profile and rank.
    *   **API-Driven:** A secure API will allow both human-facing UIs and other AI agents to interact with the marketplace.

#### 2.2.2 "Oracle" — Profiling and Assignment System
*   **Purpose:** To create deep, multi-dimensional profiles of all specialists and use them to optimize task assignment.
*   **Implementation:** This will be a new service.
*   **Features:**
    *   **Profile Database:** A new data model to store specialist profiles, including skills, cognitive traits, performance history, and stress/fatigue levels.
    *   **Data Ingestion:** Connectors to external platforms (starting with GitHub) to analyze code contributions, commit frequency, and collaboration patterns.
    *   **Cognitive Analysis:** Use NLP to analyze pull request comments and communication to infer cognitive and collaborative styles.
    *   **Assignment Engine:** An algorithm that matches tasks from Agora to the most suitable specialists, providing recommendations or, in some cases, direct assignments.

#### 2.2.3 "Hephaestus" — Automated CI/CD/CQ Pipeline
*   **Purpose:** To automate over 95% of the development lifecycle, from testing to deployment.
*   **Evolution:** This will be a major enhancement of the existing CI workflow in `.github/workflows/ci.yml`.
*   **Features:**
    *   **AI-Powered Code Review:** Katana will be integrated into the pull request process to perform initial reviews, checking for logic flaws, performance issues, and security vulnerabilities.
    *   **Automated Test Generation:** For each PR, the system will attempt to generate relevant unit and integration tests.
    *   **Predictive Deployment Analysis:** Before deployment, Hephaestus will analyze the proposed changes and historical data to generate a "risk score", predicting the potential impact on the production environment.
    *   **Continuous Quality (CQ):** The system will continuously monitor production for performance regressions or anomalies related to recent deployments.

#### 2.2.4 "Athena" — Knowledge Management and Learning System
*   **Purpose:** To transform the ecosystem into a self-learning organization.
*   **Implementation:** This will be a new service that consumes data from the other three subsystems.
*   **Features:**
    *   **Central Knowledge Base:** A unified database (e.g., a vector database combined with a traditional DB) to store all knowledge.
    *   **Data Analysis Engine:** Analyzes task outcomes from Agora, code quality from Hephaestus, and specialist performance from Oracle.
    *   **Automated Documentation:** Automatically generates and updates documentation based on successful solutions and architectural patterns.
    *   **Proactive Learning:** Identifies skill gaps in the "Legion" and proactively assigns generated training modules or recommends external courses to specialists.

## 3.0 Decomposition and Phased Implementation Plan

The project will be developed in four distinct phases, allowing for iterative delivery and feedback.

### Phase 1: Foundation & Agora (Task Marketplace)
*   **Goal:** Establish a functioning task marketplace that specialists can interact with.
*   **Key Actions:**
    1.  **DAO Layer:** Implement a robust Data Access Object layer (`src/dao`) with a persistent database (e.g., PostgreSQL) to manage tasks.
    2.  **Agora v1:** Refactor `TaskOrchestrator` to use the new DAO layer, removing the in-memory queue.
    3.  **API:** Create a basic REST or GraphQL API for `Agora` to expose tasks.
    4.  **UI v1:** Develop the `ui/` React application to display the task board. Specialists will be able to view tasks and their details.
    5.  **Refactor Agents:** Generalize `JuliusAgent` to a `BaseAgent` class.

### Phase 2: Oracle (Profiling & Intelligent Assignment)
*   **Goal:** Begin building specialist profiles and use them to provide intelligent task recommendations.
*   **Key Actions:**
    1.  **Profile Schema:** Design and implement the database schema for specialist profiles.
    2.  **GitHub Connector:** Build a service that connects to the GitHub API to pull user data (repos, commits, PRs).
    3.  **Initial Profiler:** Implement a basic profiler that analyzes commit history to extract primary programming languages and activity levels.
    4.  **Integration:** Integrate Oracle with the Agora UI to show "Recommended for You" tasks.

### Phase 3: Hephaestus (Automated Pipeline)
*   **Goal:** Augment the development process with AI-driven assistance.
*   **Key Actions:**
    1.  **AI Code Reviewer:** Create a GitHub Action that, on a pull request, sends the code diff to a Katana NLP endpoint for analysis and posts comments back to the PR.
    2.  **Test Generation Prototype:** Develop a proof-of-concept tool that uses an LLM to suggest unit tests for a given function.
    3.  **Metrics Integration:** Feed CI/CD pass/fail rates and code churn metrics into the Athena knowledge base.

### Phase 4: Athena (Knowledge & Learning)
*   **Goal:** Close the loop by creating a system that learns from and teaches the organization.
*   **Key Actions:**
    1.  **Knowledge Base Setup:** Deploy a vector database for storing embeddings of code, documentation, and task outcomes.
    2.  **Analysis Engine:** Create scheduled jobs that analyze the data in the production database to find correlations (e.g., "PRs with X characteristic are 50% more likely to cause a production issue").
    3.  **Recommendation Engine:** Implement a service that can recommend existing documentation or auto-generate new tutorials based on a specialist's recent performance.
    4.  **Feedback Loop:** Integrate Athena's insights back into Agora (to adjust task valuations) and Oracle (to update specialist profiles).

## 4.0 Conclusion

This plan provides the blueprint for realizing the vision of the Genesis Directive. It is ambitious but structured, building upon the existing codebase in a logical, phased manner. The successful execution of this plan will result in an unprecedented synergy between human and artificial intelligence.
