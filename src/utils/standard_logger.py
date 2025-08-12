import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# Note the inconsistency in experimental modules: _log_exporter is internal, metric_exporter is not.
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# --- Configuration ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "katana-ai")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


class TelemetryProvider:
    """
    A singleton class to manage OpenTelemetry setup for Logs, Metrics, and Traces.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryProvider, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self):
        if self._initialized:
            return

        resource = Resource(attributes={
            "service.name": SERVICE_NAME
        })

        # --- Trace Provider Setup ---
        trace_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(trace_provider)

        # --- Metrics Provider Setup ---
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # --- Logger Provider Setup (using experimental _logs API) ---
        log_provider = LoggerProvider(resource=resource)
        log_exporter = OTLPLogExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(log_provider)

        self._logger_provider = log_provider
        self._tracer_provider = trace_provider
        self._meter_provider = meter_provider
        self._initialized = True

        # Initial log to confirm setup
        initial_logger = self.get_logger(__name__)
        initial_logger.info(f"TelemetryProvider initialized for service '{SERVICE_NAME}'.")
        initial_logger.info(f"OTLP endpoint set to '{OTEL_EXPORTER_OTLP_ENDPOINT}'.")

    def get_logger(self, name: str, level: Optional[str] = None) -> logging.Logger:
        """
        Creates and configures a logger that is integrated with OpenTelemetry.
        """
        if not self._initialized:
            self._initialize()

        log_level_str = level or LOG_LEVEL
        log_level = getattr(logging, log_level_str, logging.INFO)

        logger = logging.getLogger(name)
        logger.setLevel(log_level)

        if logger.hasHandlers():
            logger.handlers.clear()

        otel_handler = LoggingHandler(logger_provider=self._logger_provider, level=log_level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(otel_handler)
        logger.addHandler(console_handler)

        return logger

    def get_meter(self, name: str) -> metrics.Meter:
        """
        Returns a meter from the global meter provider.
        """
        if not self._initialized:
            self._initialize()
        return metrics.get_meter(name)


# --- Global Accessors ---
_telemetry_provider = TelemetryProvider()

def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    Global function to get an OTel-configured logger.
    """
    return _telemetry_provider.get_logger(name, level)

def get_meter(name: str) -> metrics.Meter:
    """
    Global function to get an OTel-configured meter.
    """
    return _telemetry_provider.get_meter(name)
