import pika
import json
import os
import sys
import asyncio
import time
from src.agents.julius_agent import JuliusAgent
from src.orchestrator.task_orchestrator import TaskResult

# This is a placeholder for the actual JuliusAgent implementation
class MockJuliusAgent(JuliusAgent):
    async def process_tasks(self, tasks: list[str]) -> list[TaskResult]:
        results = []
        for task in tasks:
            # Simulate processing
            await asyncio.sleep(1) # Simulate I/O bound operation
            success = "fail" not in task
            details = "Task processed successfully" if success else "Task failed"
            results.append(TaskResult(success=success, details=details, task_content=task))
        return results

def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ failed. Retrying in 10 seconds...")
            time.sleep(10)

def main():
    agent = MockJuliusAgent()
    connection = connect_to_rabbitmq()
    channel = connection.channel()

    task_queue_name = os.environ.get("TASK_QUEUE_NAME", "task_queue")
    result_queue_name = os.environ.get("RESULT_QUEUE_NAME", "result_queue")

    print(f"Task queue: {task_queue_name}")
    print(f"Result queue: {result_queue_name}")

    channel.queue_declare(queue=task_queue_name, durable=True)
    channel.queue_declare(queue=result_queue_name, durable=True)

    def callback(ch, method, properties, body):
        task = body.decode()
        print(f" [x] Received {task}")

        results = asyncio.run(agent.process_tasks([task]))
        result = results[0]

        message = {
            "task": result.task_content,
            "success": result.success,
            "details": result.details,
            "queue_name": task_queue_name
        }

        print(f"Publishing result: {message}")

        channel.basic_publish(
            exchange='',
            routing_key=result_queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        print(f" [x] Sent result for {task}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=task_queue_name, on_message_callback=callback)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
