import json
import typing
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult
from opentelemetry.sdk._logs import LogData

class FileLogExporter(LogExporter):
    """
    An OpenTelemetry LogExporter that writes logs to a file,
    one JSON object per line.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        # Clear the file on initialization
        with open(self.file_path, "w"):
            pass

    def export(self, batch: typing.Sequence[LogData]) -> LogExportResult:
        with open(self.file_path, "a") as f:
            for data in batch:
                record = data.log_record
                log_entry = {
                    "body": record.body,
                    "severity_text": record.severity_text,
                    "attributes": dict(record.attributes),
                    "trace_id": f"0x{record.trace_id:032x}",
                    "span_id": f"0x{record.span_id:016x}",
                    "timestamp": record.timestamp,
                }
                f.write(json.dumps(log_entry) + "\n")
        return LogExportResult.SUCCESS

    def shutdown(self) -> None:
        pass
