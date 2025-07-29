import json
import os
import psycopg2
from kafka import KafkaConsumer

# Kafka configuration
KAFKA_TOPIC = "katana_logs"
KAFKA_BROKER = "localhost:9092"

# TimescaleDB configuration
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "katana"
DB_USER = "postgres"
DB_PASSWORD = "password"

def create_table(conn):
    """Creates the logs table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS command_logs (
                time TIMESTAMPTZ NOT NULL,
                trace_id UUID NOT NULL,
                span_id TEXT NOT NULL,
                parent_id TEXT,
                command TEXT NOT NULL,
                user_id TEXT,
                input JSONB,
                output JSONB,
                error JSONB,
                duration_ms DOUBLE PRECISION,
                metadata JSONB
            );
        """)
        cur.execute("SELECT create_hypertable('command_logs', 'time', if_not_exists => TRUE);")
        conn.commit()

def main():
    """Consumes log messages from Kafka and inserts them into TimescaleDB."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    create_table(conn)

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )

    with conn.cursor() as cur:
        for message in consumer:
            log = message.value
            cur.execute(
                """
                INSERT INTO command_logs (
                    time, trace_id, span_id, parent_id, command, user_id,
                    input, output, error, duration_ms, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    log['timestamp'],
                    log['trace_id'],
                    log['span_id'],
                    log.get('parent_id'),
                    log['command'],
                    log.get('user_id'),
                    json.dumps(log.get('input')),
                    json.dumps(log.get('output')),
                    json.dumps(log.get('error')),
                    log['duration_ms'],
                    json.dumps(log.get('metadata'))
                )
            )
            conn.commit()
            print(f"Inserted log message: {log['trace_id']}")

if __name__ == "__main__":
    main()
