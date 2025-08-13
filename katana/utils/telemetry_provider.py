import sys
import os
import json
from datetime import datetime, timezone

from opentelemetry import trace, metrics
from opentelemetry._logs import get_logger as get_otel_logger, set_logger_provider, Logger
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import ConsoleLogExporter, SimpleLogRecordProcessor
from opentelemetry.trace import set_tracer_provider
from opentelemetry.metrics import set_meter_provider
from opentelemetry._logs import SeverityNumber

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from .file_log_exporter import FileLogExporter

# The Observability Contract
# All log events in the system MUST conform to this structure.
# {
#     "timestamp": "...",         # ISO 8601 UTC timestamp
#     "trace_id": "...",          # ID of the end-to-end operation
#     "span_id": "...",           # ID of the specific step/span
#     "severity": "INFO",         # Log level (e.g., INFO, ERROR, DEBUG)
#     "event_name": "...",        # Unique, machine-readable event name (e.g., "user.login.success")
#     "body": {
#         "message": "...",       # Human-readable message (optional)
#         "user_id": "...",       # User ID, if applicable
#         "duration_ms": 123,     # Operation duration, if applicable
#         "success": true,        # Success flag, if applicable
#         "attributes": { ... }   # Flexible dictionary for event-specific context
#     }
# }

def setup_telemetry(service_name: str = "katana-service"):
    """
    Configures a unified, pure OpenTelemetry pipeline for the application.
    This setup uses the OpenTelemetry SDK directly, without bridging to standard
    logging, to ensure a clean and direct telemetry pipeline.

    Returns:
        The configured LoggerProvider instance, which can be shut down on exit.
    """
    resource = Resource.create(attributes={"service.name": service_name})

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout)))
    set_tracer_provider(tracer_provider)

    # --- Metrics ---
    metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(out=sys.stdout))
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)

    # --- Logs (Pure OTel) ---
    logger_provider = LoggerProvider(resource=resource)

    log_file_path = os.getenv("OTEL_LOG_FILE_PATH")
    log_exporter = FileLogExporter(file_path=log_file_path) if log_file_path else ConsoleLogExporter(out=sys.stderr)

    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    return logger_provider


def get_logger(name: str) -> Logger:
    """
    Returns a pure OpenTelemetry logger instance.
    """
    return get_otel_logger(name)

def get_tracer(name: str) -> trace.Tracer:
    """
    Returns a tracer instance for creating spans.
    """
    return trace.get_tracer(name)

def log_event(logger: Logger, event_name: str, body: dict, severity: SeverityNumber = SeverityNumber.INFO):
    """
    Logs a structured event according to The Observability Contract by
    constructing and emitting a LogRecord directly.
    """
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    # The OTel SDK expects timestamps in nanoseconds.
    now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

    # The body of the LogRecord will be our structured JSON string.
    log_body_dict = {
        "event_name": event_name,
        "trace_id": f"0x{span_context.trace_id:032x}",
        "span_id": f"0x{span_context.span_id:016x}",
        "timestamp": datetime.fromtimestamp(now_ns / 1e9, tz=timezone.utc).isoformat(),
        "severity": severity.name,
        "body": body
    }

    record = LogRecord(
        timestamp=now_ns,
        observed_timestamp=now_ns,
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        trace_flags=span_context.trace_flags,
        severity_text=severity.name,
        severity_number=severity,
        body=json.dumps(log_body_dict),
        resource=logger.resource,
        attributes={}, # Attributes are now inside the JSON body
    )

    logger.emit(record)

# --- Migration Adapter ---
def log_unstructured_message(logger: Logger, message: str, severity: SeverityNumber = SeverityNumber.INFO):
    """
    (Temporary Adapter) Logs an old, unstructured message by wrapping it
    in the new Observability Contract.

    This allows for gradual migration of services.
    """
    body = {
        "message": message,
        "attributes": {"legacy_log": True}
    }
    log_event(logger, "legacy.unstructured.message", body, severity)
