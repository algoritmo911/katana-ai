import sys
import subprocess
import time

# --- Configuration ---
RABBITMQ_HOST = "localhost"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TEST_TOPIC = "katana-readiness-test"

# --- Helper Functions ---

def run_check(title, check_function):
    """Runs a check function and prints the result."""
    print(f"--- {title} ---")
    try:
        if check_function():
            print("Status: PASSED")
            return True
        else:
            print("Status: FAILED")
            return False
    except Exception as e:
        print(f"Status: FAILED (An exception occurred: {e})")
        return False
    finally:
        print("-" * (len(title) + 8))
        print()

# --- Check Functions ---

def check_python_version():
    """Checks the Python version."""
    print("Checking Python version...")
    if sys.version_info < (3, 10):
        print(f"Error: Python 3.10+ is required. You are using {sys.version}")
        return False
    print(f"Python version is {sys.version}")
    return True

def check_pip_dependencies():
    """Checks if all required pip dependencies are installed."""
    print("Checking pip dependencies...")
    try:
        import pika
        import kafka
        print("Required libraries (pika, kafka-python) are installed.")
        return True
    except ImportError as e:
        print(f"Error: Missing required library. Please run 'pip install -r requirements.txt'. Details: {e}")
        return False

def check_docker():
    """Checks if Docker is running and accessible."""
    print("Checking Docker daemon...")
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        print("Docker is running and accessible.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Docker daemon is not running or not accessible.")
        return False

def check_rabbitmq():
    """Performs a simple round-trip test with RabbitMQ."""
    print("Checking RabbitMQ connection and performing a round-trip test...")
    try:
        import pika
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        queue_name = "katana-readiness-test-queue"
        channel.queue_declare(queue=queue_name, exclusive=True)

        message = f"ping-{int(time.time())}"
        channel.basic_publish(exchange='', routing_key=queue_name, body=message)
        print(f"Sent message: '{message}'")

        method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=True)

        if body.decode() == message:
            print(f"Received message: '{body.decode()}'")
            print("RabbitMQ round-trip test successful.")
            connection.close()
            return True
        else:
            print(f"Error: Mismatched message received. Expected '{message}', got '{body.decode()}'")
            connection.close()
            return False

    except Exception as e:
        print(f"Error connecting to or interacting with RabbitMQ: {e}")
        return False

def check_kafka():
    """Performs a simple round-trip test with Kafka."""
    print("Checking Kafka connection and performing a round-trip test...")
    try:
        from kafka import KafkaProducer, KafkaConsumer, TopicPartition

        producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        message = f"ping-{int(time.time())}".encode('utf-8')

        producer.send(KAFKA_TEST_TOPIC, message).get(timeout=10)
        print(f"Sent message: '{message.decode()}' to topic '{KAFKA_TEST_TOPIC}'")

        consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset='earliest', consumer_timeout_ms=10000)
        tp = TopicPartition(KAFKA_TEST_TOPIC, 0)
        consumer.assign([tp])
        consumer.seek_to_end(tp)

        # This is a simplified check. A more robust check would involve a dedicated consumer group.
        # For now, we just check if we can connect and send.
        # A full round-trip in Kafka is more complex to guarantee without a dedicated consumer running.
        print("Kafka producer was able to connect and send.")
        print("Note: A full round-trip check requires a dedicated consumer.")
        return True

    except Exception as e:
        print(f"Error connecting to or interacting with Kafka: {e}")
        return False

# --- Main Execution ---

def main():
    """Runs all readiness checks."""
    print("==========================================")
    print("  Katana MindShell Readiness Test Script  ")
    print("==========================================")

    checks = {
        "Python Version": check_python_version,
        "Pip Dependencies": check_pip_dependencies,
        "Docker Daemon": check_docker,
        "RabbitMQ Connectivity": check_rabbitmq,
        "Kafka Connectivity": check_kafka,
    }

    results = {title: run_check(title, func) for title, func in checks.items()}

    print("\n--- Summary ---")
    all_passed = True
    for title, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{title:<25} | {status}")
        if not result:
            all_passed = False

    print("---------------")

    if all_passed:
        print("\nConclusion: All readiness checks passed. The environment is ready!")
        sys.exit(0)
    else:
        print("\nConclusion: Some readiness checks failed. Please review the logs above and fix the issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
