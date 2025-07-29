from fastapi import FastAPI, Query
import pika
import json
import threading
import time
from collections import defaultdict
import os

app = FastAPI()

metrics = defaultdict(list)

def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ failed. Retrying in 10 seconds...")
            time.sleep(10)

def consume_results():
    connection = connect_to_rabbitmq()
    channel = connection.channel()

    result_queue_name = os.environ.get("RESULT_QUEUE_NAME", "result_queue")
    channel.queue_declare(queue=result_queue_name, durable=True)

    def callback(ch, method, properties, body):
        result = json.loads(body.decode())
        queue_name = result.get("queue_name")
        if queue_name:
            metrics[queue_name].append(result)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=result_queue_name, on_message_callback=callback)
    channel.start_consuming()

@app.on_event("startup")
def startup_event():
    threading.Thread(target=consume_results, daemon=True).start()

@app.get("/metrics")
async def get_metrics(queue_name: str = Query(..., min_length=1)):
    return metrics.get(queue_name, [])

@app.delete("/metrics")
async def clear_metrics(queue_name: str = Query(..., min_length=1)):
    if queue_name in metrics:
        del metrics[queue_name]
    return {"message": f"Metrics for queue {queue_name} cleared"}
