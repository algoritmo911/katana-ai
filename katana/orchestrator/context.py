class Context:
    def __init__(self):
        self.env = {}
        self.results = {}

    def set_env(self, key, value):
        self.env[key] = value

    def get_env(self, key):
        return self.env.get(key)

    def set_result(self, key, value):
        self.results[key] = value

    def get_result(self, key):
        return self.results.get(key)
