# Technical Design Document: Morpheus Protocol

## Abstract

The Morpheus Protocol is a system designed to provide Katana with autonomous self-regulation, optimization, and maintenance capabilities. It introduces a "homeostasis loop" that activates during periods of low system activity (a "sleep" state). During this state, Morpheus will perform a deep system analysis, identify areas for improvement (e.g., technical debt, performance degradation), and then autonomously plan and execute tasks to address these findings. This transforms Katana from a purely reactive agent into a proactive, self-improving system.

---

## 1. Component: `Circadian Rhythm` (The "Sleep" Trigger)

This component is responsible for determining when the system is idle and can safely begin the Morpheus protocol. The trigger must be reliable, ensuring that maintenance tasks do not interfere with active user requests or critical operations.

### 1.1. Defining "Low Activity"

A simple "no requests for N minutes" trigger is insufficient as it doesn't account for ongoing, non-user-facing background tasks. We will use a composite metric to define the "low activity" state. The system will be considered "asleep" if **all** of the following conditions are met for a sustained period (e.g., 15 minutes):

1.  **API Request Volume:** The number of incoming API requests per minute is below a configurable threshold (e.g., `< 5 requests/min`). This is the primary indicator of user-facing inactivity.
2.  **Active Orchestrator Sessions:** The number of currently active `Orchestrator` execution loops is zero. This ensures we don't interrupt a complex task already in progress.
3.  **Chronos Queue Depth:** The number of pending tasks in the "high-priority" Chronos queue is zero. This prevents Morpheus from competing with critical, scheduled background jobs. Low-priority queues (e.g., for logging) can be ignored.
4.  **CPU/Resource Utilization (Secondary Check):** System-wide CPU and memory utilization are below a "baseline" threshold (e.g., `< 20% CPU`). This is a safeguard against unknown processes or runaway tasks that wouldn't be captured by the metrics above.

These metrics will be collected by the "Oracle" monitoring service and exposed via an internal health-check endpoint.

### 1.2. Trigger Mechanism

We will leverage the existing **Chronos** asynchronous task scheduling system to implement the trigger.

1.  **A recurring Chronos job (`morpheus_check_for_sleep`)** will be scheduled to run at a high frequency (e.g., every 5 minutes).
2.  When this job runs, it will query the Oracle's health-check endpoint to retrieve the composite "low activity" metrics described in section 1.1.
3.  The job will maintain a small, persistent state (e.g., in Redis) to track the *duration* of the low-activity state. It will record a timestamp when the low-activity state is first detected.
4.  **Activation Condition:** If the `morpheus_check_for_sleep` job determines that the low-activity conditions have been continuously met for the required duration (e.g., `current_time - start_timestamp > 15 minutes`), it will then enqueue the main **`morpheus_protocol_start`** task into a dedicated, low-priority Chronos queue.
5.  **Deactivation:** If the low-activity conditions are broken at any point, the job resets the "start timestamp," effectively canceling the countdown to sleep.

This design ensures that the Morpheus protocol is only initiated after a *sustained* period of idleness and will not interfere with user activity or critical system tasks.

---

## 2. Component: `Dream Analyzer` (System Self-Diagnosis)

Once the `Circadian Rhythm` component triggers the "sleep" state, the `Dream Analyzer` is activated. Its purpose is to perform a comprehensive, multi-faceted health check of the entire Katana ecosystem. This is not a single tool, but a diagnostic pipeline that orchestrates several existing capabilities to build a holistic view of the system's state.

### 2.1. The Diagnostic Pipeline

The `Dream Analyzer` will be implemented as a master `Orchestrator` plan. This plan is pre-defined and hardcoded, as its purpose is purely diagnostic and should be consistent. It will execute the following sequence of capabilities:

**Step 1: Code Health Audit**
*   **Capability:** `run_code_scanner`
*   **Parameters:** `{ "target_directory": "/", "complexity_threshold": 25, "scan_for_new_debt_only": true }`
*   **Purpose:** To identify new or recently modified code that exceeds acceptable complexity thresholds or contains other "code smells." The `scan_for_new_debt_only` parameter ensures it doesn't repeatedly flag known, legacy technical debt, focusing instead on recent regressions.
*   **Output:** A list of file paths and line numbers with high technical debt scores.

**Step 2: Performance Regression Analysis**
*   **Capability:** `query_oracle_performance_metrics`
*   **Parameters:** `{ "time_window": "24h", "percentile": 95, "regression_threshold_ms": 500 }`
*   **Purpose:** To query the Oracle monitoring system for API endpoint performance data. It will specifically look for endpoints whose 95th percentile latency has increased by more than the specified threshold compared to the previous 24-hour period.
*   **Output:** A list of degraded API endpoints and their performance deltas.

**Step 3: Knowledge Graph Integrity Check**
*   **Capability:** `audit_noosphere_integrity`
*   **Parameters:** `{ "check_for_orphans": true, "check_for_contradictions": true }`
*   **Purpose:** To scan the Noosphere (knowledge graph) for structural and logical inconsistencies.
    *   *Orphans*: Concepts that are not connected to the main graph.
    *   *Contradictions*: Entities with mutually exclusive properties (e.g., a concept being both a "subclass of A" and "disjoint with A").
*   **Output:** A list of orphaned concepts and contradictory fact pairs.

**Step 4: Emotional Resonance Hotspot Analysis**
*   **Capability:** `analyze_chimera_resonance`
*   **Parameters:** `{ "time_window": "72h", "resonance_threshold": 0.9, "stability_period": "24h" }`
*   **Purpose:** To identify "hotspots" in the Chimera (emotional/conceptual resonance map). This capability will find concepts that have maintained a consistently high "stress" or "confusion" resonance for a significant period. This may indicate underlying user confusion, a flawed concept, or a problematic area of the system's understanding that requires attention.
*   **Output:** A list of concepts with high, stable stress resonance.

### 2.2. Aggregated Diagnostic Report

The output of this pipeline is not a single result, but a collection of structured data from each step. The final action of the `Dream Analyzer` is to aggregate these findings into a single, structured JSON object: the **`AggregatedDiagnosticReport`**. This report will be the primary input for the next stage of the Morpheus protocol, the `Dream Architect`.

**Example `AggregatedDiagnosticReport`:**
```json
{
  "report_id": "morpheus-diag-2025-08-12-125515",
  "findings": {
    "code_debt": [
      { "file": "orchestrator/main.py", "line": 95, "complexity": 28 }
    ],
    "performance_regressions": [
      { "endpoint": "/api/v2/planner", "latency_increase_ms": 850 }
    ],
    "knowledge_integrity_issues": [
      { "type": "orphan", "concept_id": "uuid-123-abc" }
    ],
    "resonance_hotspots": [
      { "concept": "Self-Correction Loop", "stress_level": 0.92 }
    ]
  }
}
```
This structured report forms the raw material from which actionable plans will be built.

---

## 3. Component: `Dream Architect` (Intent Generation & Prioritization)

The `Dream Architect` receives the `AggregatedDiagnosticReport` from the `Dream Analyzer`. Its purpose is twofold: first, to translate the raw, structured findings into formal, actionable tasks, and second, to prioritize these tasks to ensure that the most critical issues are addressed first.

### 3.1. Intent Generation via "Prometheus Protocol"

For each finding in the diagnostic report, the `Dream Architect` will generate a corresponding `IntentContract`. This process, named the **"Prometheus Protocol,"** is a sophisticated mapping layer that converts a problem statement into a goal-oriented directive suitable for the `Orchestrator`. This is not a simple 1-to-1 mapping; it involves an LLM call to formulate a high-quality, human-like goal.

The process for each finding is as follows:

1.  **Select a Finding:** E.g., `{ "file": "orchestrator/main.py", "line": 95, "complexity": 28 }`.
2.  **Lookup Template:** A template is chosen based on the finding type (`code_debt`, `performance_regressions`, etc.).
3.  **Invoke LLM for Goal Formulation:** An LLM is called with a specialized prompt containing the finding's data and the template.
    *   **Example Prompt for Code Debt:**
        ```
        You are a senior software engineer. A automated scan found a piece of code with high cyclomatic complexity. Formulate a clear, concise goal for a junior engineer to fix it.
        Problem Data: { "file": "orchestrator/main.py", "line": 95, "complexity": 28 }
        Goal: Refactor the function at orchestrator/main.py around line 95 to reduce its cyclomatic complexity from 28 to below 20.
        ```
4.  **Construct `IntentContract`:** The LLM's output is used to build the final `IntentContract`.
    *   **Resulting `IntentContract`:**
        ```json
        {
          "goal": "Refactor the function at orchestrator/main.py around line 95 to reduce its cyclomatic complexity from 28 to below 20.",
          "constraints": ["Must pass all existing unit tests.", "Should not alter public-facing API signatures."],
          "source": "morpheus-protocol",
          "raw_finding": { ... }
        }
        ```
This ensures that each self-generated task is as well-defined as a task given by a human operator.

### 3.2. Prioritization Model

Once a list of `IntentContract`s is generated, they must be prioritized. We cannot use a simple FIFO queue. The prioritization will be calculated as a weighted score based on several factors. Each generated intent is assigned a priority score:

**`PriorityScore = (Impact * Urgency) + (Severity * 0.5)`**

*   **Impact (1-10):** How much of the system or user base is affected?
    *   *High (9-10):* System-wide performance degradation, critical security vulnerability.
    *   *Medium (4-8):* High-traffic API endpoint regression, significant technical debt in a core module.
    *   *Low (1-3):* Minor code smell, knowledge graph inconsistency in a non-critical area.
*   **Urgency (1-10):** How quickly will this problem get worse if left unaddressed?
    *   *High (9-10):* Security issues, data corruption bugs.
    *   *Medium (4-8):* Performance regressions that are trending upwards.
    *   *Low (1-3):* Stable technical debt.
*   **Severity (1-10):** What is the raw severity of the finding?
    *   This is often derived directly from the diagnostic tool (e.g., a complexity score of 28 is more severe than 15).

**Mapping Findings to Scores:**
A set of rules will map each finding type to a baseline score for these factors:

| Finding Type                  | Base Impact | Base Urgency | Severity Mapping                    |
| ----------------------------- | :---------: | :----------: | ----------------------------------- |
| **Performance Regression**    |      8      |      7       | Proportional to latency increase    |
| **Code Debt**                 |      5      |      3       | Proportional to complexity score    |
| **Knowledge Contradiction**   |      4      |      6       | Fixed score                         |
| **Resonance Hotspot**         |      3      |      4       | Proportional to stress level        |

The `Dream Architect`'s final output is a **Prioritized Task List**, an ordered list of `IntentContract`s. This list is then passed to the final component, `REM Sleep`, for execution.

---

## 4. Component: `REM Sleep` (Autonomous & Safe Execution)

This component is the "hands" of the Morpheus protocol. It takes the prioritized list of `IntentContract`s from the `Dream Architect` and executes them one by one. The paramount design principle for this component is **safety**. Autonomous actions, especially those involving code modification, must be performed in a way that guarantees system stability.

### 4.1. The Safe Execution Loop

The `REM Sleep` component iterates through the prioritized task list, executing one task at a time. For each `IntentContract`, it performs the following steps in a strict, sequential manner:

1.  **Isolate the Environment:** Before any action is taken, a new, isolated git branch is created from the current `main` branch. The branch name will be descriptive, e.g., `morpheus/refactor-main-orchestrator-20250812`. All subsequent code modifications will happen on this branch.

2.  **Invoke the Orchestrator:** The `IntentContract`'s `goal` is passed to the core `Orchestrator`'s `run_orchestrator` function. The `Orchestrator` proceeds as usual, using its own capabilities and self-correction loop to achieve the goal (e.g., refactoring the code).

3.  **Post-Execution Verification (The "Centurion" Check):** After the `Orchestrator` reports success, the "work" is not yet done. The changes, which exist only on the isolated branch, must be rigorously verified by the **"Centurion"** automated quality gate. This is a critical safety step. "Centurion" will:
    a.  Run the **full suite of unit tests**.
    b.  Run the **full suite of integration tests**.
    c.  Run a **linter and static analysis** check to ensure code quality hasn't degraded.

4.  **Evaluate Verification Results:**
    *   **If all Centurion checks pass:** The task is considered a success. The isolated git branch is merged into `main`.
    *   **If *any* Centurion check fails:** The task is considered a failure. The system must be returned to its original state.

### 4.2. Automatic Rollback Mechanism

Failure during the "Centurion" check triggers an automatic rollback:

1.  **Log the Failure:** Detailed logs of the failure (e.g., which tests failed) are captured and associated with the `IntentContract`. This is crucial for future learning.
2.  **Abandon Changes:** The isolated git branch (`morpheus/refactor-...`) is **deleted**, not merged. This instantly and cleanly discards all changes made during the attempt.
3.  **Update Task Status:** The `IntentContract` is marked as "failed_execution" in a persistent log, preventing Morpheus from retrying the exact same failed task in the next sleep cycle.
4.  **Continue to Next Task:** The `REM Sleep` loop moves to the next highest-priority task in the list.

This git-based isolation and rollback mechanism provides a powerful and nearly foolproof way to attempt complex tasks without risking the stability of the main codebase.

### 4.3. Memory Consolidation

After a task is successfully completed and merged, its impact must be recorded. This is the "memory consolidation" phase.

1.  **Update Noosphere:** A call is made to the `update_noosphere_state` capability.
2.  **Payload:** The payload includes the original `IntentContract` and a summary of the successful changes (e.g., "Cyclomatic complexity of `orchestrator/main.py` reduced from 28 to 19.").
3.  **Purpose:** This creates a new node in the knowledge graph, linking the "problem" (the initial finding) to the "solution" (the successful autonomous action). This serves as a permanent record of the system's self-improvement activities, which can be queried by human operators and used by the system itself to inform future decisions.

This completes the Morpheus loop: a cycle of rest, diagnosis, planning, safe execution, and memory consolidation that allows the system to autonomously maintain and improve itself over time.
