import json
import time
import uuid
from datetime import datetime
from kafka import KafkaProducer

# Kafka configuration
KAFKA_TOPIC = "katana_logs"
KAFKA_BROKER = "localhost:9092"

def create_log_message():
    """Creates a dummy log message."""
    return {
        "trace_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4()),
        "parent_id": None,
        "timestamp": datetime.now().isoformat(),
        "command": "dummy_command",
        "user_id": "dummy_user",
        "input": {"args": [1, "foo"], "kwargs": {"bar": "baz"}},
        "output": {"result": "success"},
        "error": None,
        "duration_ms": 123.45,
        "metadata": {"host": "dummy_host"}
    }

def main():
    """Produces dummy log messages to Kafka."""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    while True:
        log_message = create_log_message()
        producer.send(KAFKA_TOPIC, log_message)
        print(f"Sent log message: {log_message['trace_id']}")
        time.sleep(2)

if __name__ == "__main__":
    main()
