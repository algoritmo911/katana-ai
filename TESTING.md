# Katana MindShell - Test Scenarios

This document outlines the testing strategy and scenarios for the first release of the Katana MindShell.

## 1. Unit Tests

Unit tests are written using `pytest` and are located in the `tests/unit` directory. They are designed to be fast and isolated, using mocks for external dependencies.

**Key Scenarios:**

*   **Command Logic:** Test the `run()` method of each command with valid and invalid arguments.
*   **DSL Parser:** Test the parsing of valid and invalid DSL syntax.
*   **DSL Interpreter:** Test the interpretation of different DSL constructs (e.g., command chaining, variable assignment).
*   **Utility Functions:** Test all utility functions with various inputs.

**Execution:**

```bash
pytest tests/unit
```

## 2. Integration Tests

Integration tests are located in the `tests/integration` directory. They test the interaction between different modules and with external services like RabbitMQ and Kafka.

**Key Scenarios:**

*   **End-to-End Command Execution:** Test the full execution of a command from the CLI to the command runner and back.
*   **Asynchronous Task Execution:** Test the execution of a command as an asynchronous task via the task queue.
*   **Message Broker Communication:** Test the publishing and consuming of messages from RabbitMQ and Kafka.
*   **AI Integration:** Test the interaction with the AI models, including sending prompts and receiving responses.

**Execution:**

```bash
pytest tests/integration
```

## 3. Stress Tests

Stress tests are located in the `tests/stress` directory. They are designed to test the performance and stability of the system under high load.

**Key Scenarios:**

*   **High Command Concurrency:** Simulate a large number of concurrent users executing commands.
*   **Large Task Queue:** Enqueue a large number of tasks in the task queue to test the worker's performance.
*   **High Message Volume:** Publish a large number of messages to RabbitMQ and Kafka to test the message broker's performance.

**Execution:**

```bash
# (Example using locust)
locust -f tests/stress/locustfile.py
```

## 4. Smoke Tests

Smoke tests are a small subset of the integration tests that are run against the production environment after a deployment to ensure that the system is running correctly.

**Key Scenarios:**

*   **`status` command:** Run the `katana status` command to check the health of the system.
*   **`log` command:** Run the `katana log` command to check if logging is working.
*   **Basic AI query:** Run a simple AI query to check the AI integration.

**Execution:**

```bash
pytest --smoke
```

## 5. Test Automation

All tests are integrated into the CI/CD pipeline (GitHub Actions).

*   **Unit and Integration Tests:** Run on every push and pull request.
*   **Stress Tests:** Run manually before a major release.
*   **Smoke Tests:** Run automatically after every deployment to production.
