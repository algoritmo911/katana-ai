from fastapi import FastAPI, Request
import logging

app = FastAPI()

tokens = {}

logging.basicConfig(level=logging.INFO)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/oauth/token")
def get_token(request: Request):
    logging.info(f"Received token request from {request.client.host}")
    return {"access_token": "dummy_token", "token_type": "bearer"}
