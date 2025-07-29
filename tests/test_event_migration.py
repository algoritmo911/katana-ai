import unittest
import os
import shutil
from katana.event_store.event_store import EventStore
from katana.event_store.schema_registry import SchemaRegistry
from katana.event_store.migrator import Migrator

class TestEventMigration(unittest.TestCase):

    def setUp(self):
        self.db_path = "test_event_store.db"
        self.snapshot_path = "test_snapshots"
        self.schema_registry = SchemaRegistry()
        self.migrator = Migrator(self.schema_registry)
        self.event_store = EventStore(self.db_path, self.snapshot_path, self.schema_registry, self.migrator)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.snapshot_path):
            shutil.rmtree(self.snapshot_path)

    def test_event_migration(self):
        # Register schemas
        self.schema_registry.register("USER_CREATED", {"type": "object", "properties": {"name": {"type": "string"}}}, version=1)
        self.schema_registry.register("USER_CREATED", {"type": "object", "properties": {"full_name": {"type": "string"}}}, version=2)

        # Register migration
        def migrate_v1_to_v2(event):
            event["payload"]["full_name"] = event["payload"].pop("name")
            return event
        self.migrator.register_migration("USER_CREATED", 1, 2, migrate_v1_to_v2)

        # Append an old event
        self.event_store.append("USER_CREATED", "user1", {"name": "John Doe"}, version=1)

        # Get events and check if they are migrated
        _, events = self.event_store.get_events_for_aggregate("user1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["version"], 2)
        self.assertEqual(events[0]["payload"]["full_name"], "John Doe")
        self.assertNotIn("name", events[0]["payload"])

if __name__ == '__main__':
    unittest.main()
