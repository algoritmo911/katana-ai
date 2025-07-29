from .schema_registry import SchemaRegistry

class Migrator:
    def __init__(self, schema_registry: SchemaRegistry):
        self.schema_registry = schema_registry
        self.migration_functions = {}

    def register_migration(self, event_type, from_version, to_version, migration_func):
        if event_type not in self.migration_functions:
            self.migration_functions[event_type] = {}
        if from_version not in self.migration_functions[event_type]:
            self.migration_functions[event_type][from_version] = {}
        self.migration_functions[event_type][from_version][to_version] = migration_func

    def migrate(self, event):
        event_type = event["event_type"]
        current_version = event.get("version", 1)
        latest_version = self.schema_registry.get_latest_version(event_type)

        if current_version == latest_version:
            return event

        migrated_event = event
        for version in range(current_version, latest_version):
            migration_func = self.migration_functions.get(event_type, {}).get(version, {}).get(version + 1)
            if migration_func:
                migrated_event = migration_func(migrated_event)
                migrated_event["version"] = version + 1
            else:
                # If no migration function is found, we can either raise an error
                # or just return the event as is. For now, we'll just return it.
                break

        return migrated_event
