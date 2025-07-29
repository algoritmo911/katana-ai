import pika
import json
import os
import sys
import asyncio
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

def main():
    agent = MockJuliusAgent()
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_declare(queue='result_queue', durable=True)

    def callback(ch, method, properties, body):
        task = body.decode()
        print(f" [x] Received {task}")

        results = asyncio.run(agent.process_tasks([task]))
        result = results[0]

        message = {
            "task": result.task_content,
            "success": result.success,
            "details": result.details
        }

        channel.basic_publish(
            exchange='',
            routing_key='result_queue',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        print(f" [x] Sent result for {task}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='task_queue', on_message_callback=callback)

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
