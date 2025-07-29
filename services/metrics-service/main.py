from fastapi import FastAPI
import pika
import json
import threading

app = FastAPI()

metrics = []

def consume_results():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='result_queue', durable=True)

    def callback(ch, method, properties, body):
        result = json.loads(body.decode())
        metrics.append(result)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='result_queue', on_message_callback=callback)
    channel.start_consuming()

@app.on_event("startup")
def startup_event():
    threading.Thread(target=consume_results, daemon=True).start()

@app.get("/metrics")
async def get_metrics():
    return metrics
