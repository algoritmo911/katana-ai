import json
import os
import psycopg2
from kafka import KafkaConsumer
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Kafka configuration
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "katana_logs")
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

# TimescaleDB configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "katana")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")

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
    logging.info("Starting Hydra Observer")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        create_table(conn)
        logging.info("Database connection successful and table created.")
    except psycopg2.OperationalError as e:
        logging.error(f"Could not connect to database: {e}")
        return

    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            auto_offset_reset='earliest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        logging.info("Kafka consumer created successfully.")
    except Exception as e:
        logging.error(f"Could not create Kafka consumer: {e}")
        return

    with conn.cursor() as cur:
        for message in consumer:
            log = message.value
            try:
                cur.execute(
                    """
                    INSERT INTO command_logs (
                        time, trace_id, span_id, parent_id, command, user_id,
                        input, output, error, duration_ms, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        log.get('timestamp'),
                        log.get('trace_id'),
                        log.get('span_id'),
                        log.get('parent_id'),
                        log.get('command'),
                        log.get('user_id'),
                        json.dumps(log.get('input')),
                        json.dumps(log.get('output')),
                        json.dumps(log.get('error')),
                        log.get('duration_ms'),
                        json.dumps(log.get('metadata'))
                    )
                )
                conn.commit()
                logging.info(f"Inserted log message: {log.get('trace_id')}")
            except Exception as e:
                logging.error(f"Error inserting log message: {e}")
                conn.rollback()

if __name__ == "__main__":
    main()
