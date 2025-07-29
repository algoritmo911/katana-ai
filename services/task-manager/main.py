from fastapi import FastAPI
import pika

app = FastAPI()

@app.post("/tasks")
async def add_tasks(tasks: list[str]):
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)

    for task in tasks:
        channel.basic_publish(
            exchange='',
            routing_key='task_queue',
            body=task,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
    connection.close()
    return {"message": "Tasks added successfully"}
