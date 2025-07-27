import uuid

class UserSession:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.memory = {}

    def get(self, key):
        return self.memory.get(key)

    def set(self, key, value):
        self.memory[key] = value
