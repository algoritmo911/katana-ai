# Katana Internal Services

This directory contains internal services for the Katana project.

## AutoHealer Service

The `AutoHealer` is a microservice responsible for responding to operational anomalies within the Katana ecosystem. It acts as an autonomous immune system, triggering corrective actions when problems are detected.

### How it Works

1.  **Anomaly Listener**: The service runs a FastAPI server (`healer_server.py`) that listens for incoming anomaly notifications on the `/anomaly` endpoint. This endpoint is designed to be called by an observability service like `HydraObserver`.

2.  **Reflex Map**: The core logic is driven by the `reflex_map.yml` file. This configuration file maps specific anomaly names (e.g., `api_latency.coinbase.high`) to predefined corrective workflows (e.g., `run_coinbase_health_check_and_clear_cache`).

3.  **Workflow Execution**: When a known anomaly is received, the `AutoHealer` looks up the corresponding workflow in the reflex map and triggers it. In the current implementation, this is a logged action. In a full production setup, this would involve making an HTTP request to an n8n webhook or another workflow automation tool.

4.  **Logging**: All actions taken by the `AutoHealer` are logged with a `CRITICAL` severity to ensure they are captured with high priority. These logs create a traceable record of all self-healing actions, which can be fed back into the monitoring system.

### Running the Service

To run the AutoHealer service locally:

1.  Ensure all dependencies are installed from the root `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

2.  Run the FastAPI server using `uvicorn` from the root of the project:
    ```bash
    uvicorn katana.healer_server:app --reload
    ```

    The server will be available at `http://127.0.0.1:8000`.

### Testing

To run the unit tests for the AutoHealer:

```bash
python -m pytest katana/tests/test_auto_healer.py
```

### Example API Call

You can send a test anomaly to the running service using `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/anomaly" \
-H "Content-Type: application/json" \
-d '{
  "name": "api_latency.coinbase.high",
  "details": {
    "latency_ms": 5000,
    "region": "us-east-1"
  }
}'
```

The service will log the corresponding corrective action to the console.
