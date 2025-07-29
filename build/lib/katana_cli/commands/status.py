import json

def get_status():
    return {
        "uptime": "1h 22m",
        "tasks": 0,
        "version": "0.0.1-dev"
    }

def run():
    print(json.dumps(get_status(), indent=4))
