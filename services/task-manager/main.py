from fastapi import FastAPI, Query
import pika
import time

app = FastAPI()

def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ failed. Retrying in 10 seconds...")
            time.sleep(10)

@app.post("/tasks")
async def add_tasks(tasks: list[str], queue_name: str = Query(..., min_length=1)):
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    for task in tasks:
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=task,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
    connection.close()
    return {"message": "Tasks added successfully"}
