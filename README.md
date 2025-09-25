# katana-ai

## Development Environment Setup

### Prerequisites
- Python 3.x
- pip
- Docker (for Redis)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd katana-ai
```

### 2. Install Dependencies
It's recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
Install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Set Up Pre-commit Hooks
Pre-commit hooks help ensure code quality before you commit.
```bash
pip install pre-commit
pre-commit install
```
Now, `black` and `flake8` will run automatically on changed files before each commit.

### 4. API Keys and Secrets Management (`secrets.toml`)

For integrations with external services that require API keys or other secrets, this project uses a `secrets.toml` file.

-   **Template:** A template file `secrets.toml.example` is provided in the repository.
-   **Local Setup:**
    1.  Copy `secrets.toml.example` to a new file named `secrets.toml` in the project root.
    2.  Edit `secrets.toml` and fill in your actual API keys and other secret values.
-   **Security:**
    -   The `secrets.toml` file is **explicitly ignored by Git** (via `.gitignore`).
    -   **DO NOT COMMIT YOUR `secrets.toml` FILE.**

## Legion Architecture: Orchestrator and Workers

The Katana AI project includes a distributed agent architecture named "Legion". This system is designed to handle complex tasks by breaking them down into smaller pieces and distributing them among specialized worker agents.

### Core Components

1.  **Task Queue (`katana/task_queue`)**: The communication backbone of the system. It uses Redis as a message broker to queue tasks. All tasks are represented by a `Task` object and managed by the `TaskQueueService`.

2.  **OrchestratorAgent (`katana/orchestrator_agent.py`)**: The "brain" of the system. The orchestrator decomposes complex queries into sub-tasks, dispatches them to the queue, awaits their completion, and synthesizes the results.

3.  **Workers (`worker.py`)**: Standalone, specialized processes that listen for tasks on the queue. Each worker has "executors" for the tasks it can handle.

### How to Run the System Locally

To run the full Legion system, you need at least two processes running: the main FastAPI application and one or more worker processes.

**1. Start Redis:**
The system requires a running Redis instance. Use the provided Docker Compose file to start one easily.
```bash
docker compose up -d redis
```

**2. Start the Main Application:**
This runs the FastAPI server, which includes the Telegram bot integration and the `OrchestratorAgent`.
```bash
# In your activated virtual environment
uvicorn main:app --reload
```

**3. Start the Worker(s):**
In a separate terminal, run the `worker.py` script. You can run multiple instances of this script to scale up the processing power.
```bash
# In another terminal, with the virtual environment activated
PYTHONPATH=. python worker.py
```
The worker process will connect to Redis and start listening for jobs dispatched by the Orchestrator.

## Running Checks and Tests Locally

To ensure your code is clean, formatted, and all tests pass before pushing changes, use the `run_checks.sh` script:

```bash
./run_checks.sh
```
This script will:
1. Run `flake8` for linting.
2. Run `black` to format the code.
3. Run `pytest` with `coverage` to execute unit tests.

## Continuous Integration (CI) Pipeline

The project uses GitHub Actions for CI. The workflow is defined in `.github/workflows/ci.yml`. When you push changes, the CI pipeline automatically runs all the checks and tests.

## Troubleshooting

For common issues and their solutions, please refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).