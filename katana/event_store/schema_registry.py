class SchemaRegistry:
    def __init__(self):
        self.schemas = {}

    def register(self, event_type, schema, version=1):
        if event_type not in self.schemas:
            self.schemas[event_type] = {}
        self.schemas[event_type][version] = schema

    def get_schema(self, event_type, version=None):
        if event_type not in self.schemas:
            return None
        if version is None:
            # Return the latest version
            return self.schemas[event_type][max(self.schemas[event_type].keys())]
        return self.schemas[event_type].get(version)

    def get_latest_version(self, event_type):
        if event_type not in self.schemas:
            return None
        return max(self.schemas[event_type].keys())
