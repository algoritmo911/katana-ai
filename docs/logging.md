# Standardized Observability with OpenTelemetry

This document describes the standardized observability system used in the Katana project, which is built upon the OpenTelemetry standard.

## Overview

The project has fully transitioned from standard Python logging to a unified OpenTelemetry-based system for all three pillars of observability: **Logs, Traces, and Metrics**. This is orchestrated by the `TelemetryProvider` located in `src/utils/standard_logger.py`.

The primary goal is to create a **unified telemetric fabric**, where every piece of data is interconnected. Every log record is automatically enriched with the current `trace_id` and `span_id`, allowing you to correlate a specific log message with the exact distributed trace and operation that produced it.

## The `TelemetryProvider`

The `TelemetryProvider` is a singleton class that handles the setup of the entire OpenTelemetry pipeline:

1.  **Resource Identification**: It creates a `Resource` that identifies all telemetry as originating from the `katana-ai` service (or as configured by `SERVICE_NAME`).
2.  **Trace Provider**: It configures a `TracerProvider` to generate and process distributed traces.
3.  **Log Provider**: It configures a `LoggerProvider` to handle log records.
4.  **Exporters**: It sets up OTLP (OpenTelemetry Protocol) exporters to send all telemetry data to a configured collector endpoint.

## Configuration

The observability system is configured using the following environment variables:

-   `SERVICE_NAME`: The name of the service that will be attached to all telemetry signals. Defaults to `katana-ai`.
-   `OTEL_EXPORTER_OTLP_ENDPOINT`: The gRPC endpoint of the OpenTelemetry collector (e.g., `http://localhost:4317`).
-   `LOG_LEVEL`: The minimum level for logs to be processed. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. The default is `INFO`.

## Usage

While the backend has been completely replaced, the usage in code remains simple and familiar. To get a logger, you use the same function as before:

```python
from src.utils.standard_logger import get_logger

# This logger is now fully integrated with OpenTelemetry
logger = get_logger(__name__)

# When you create a log inside a trace, it will be automatically correlated.
logger.info("This is an info message.")
logger.warning("This is a warning message.")
```

The `get_logger` function now returns a standard Python logger instance that has been hooked into the OpenTelemetry `LoggerProvider` via a `LoggingHandler`. This ensures that all logs are processed and exported through the OpenTelemetry pipeline.

## Log Rotation and Local Files

The new system **sends logs to a central collector** instead of managing local log files directly. The concept of log rotation is now handled by the collector and the downstream logging service (e.g., Loki, Elasticsearch), not by the application itself.

For local development, the logger is also configured to output to the console (`StreamHandler`) for immediate feedback.
