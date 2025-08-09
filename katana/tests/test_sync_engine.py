import unittest
import os
import json
import shutil
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from katana.core.sync_engine import SyncEngine
from katana.core.user_profile import UserProfile
from katana.adapters.local_file_adapter import LocalFileAdapter
from katana.adapters.mock_cloud_adapter import MockCloudAdapter
import dataclasses

class TestSyncEngine(unittest.TestCase):

    def setUp(self):
        self.test_user_data_dir = Path("test_user_data_temp_dir")
        self.test_user_data_dir.mkdir(parents=True, exist_ok=True)
        self.remote_db_file = Path("test_remote_db.json")

        self.local_storage = LocalFileAdapter(self.test_user_data_dir)
        self.remote_storage = MockCloudAdapter(self.remote_db_file)
        self.sync_engine = SyncEngine(self.local_storage, self.remote_storage)

    def tearDown(self):
        if self.test_user_data_dir.exists():
            shutil.rmtree(self.test_user_data_dir)
        if self.remote_db_file.exists():
            os.remove(self.remote_db_file)

    def test_push(self):
        user_id = 123
        profile = UserProfile(user_id)
        profile.add_command_to_history("test command")
        self.local_storage.save(user_id, dataclasses.asdict(profile))

        self.sync_engine.push(user_id)

        remote_data = self.remote_storage.load(user_id)
        self.assertIsNotNone(remote_data)
        self.assertEqual(remote_data['user_id'], user_id)
        self.assertEqual(remote_data['command_history'][0]['command'], "test command")

    def test_pull(self):
        user_id = 456
        profile_data = {"user_id": user_id, "command_history": [{"command": "remote command", "timestamp": "now"}]}
        self.remote_storage.save(user_id, profile_data)

        self.sync_engine.pull(user_id)

        local_data = self.local_storage.load(user_id)
        self.assertIsNotNone(local_data)
        self.assertEqual(local_data['command_history'][0]['command'], "remote command")

    def test_get_sync_status(self):
        user_id = 789

        # Test "not found"
        self.assertEqual(self.sync_engine.get_sync_status(user_id), "not found")

        # Test "local only"
        profile = UserProfile(user_id)
        self.local_storage.save(user_id, dataclasses.asdict(profile))
        self.assertEqual(self.sync_engine.get_sync_status(user_id), "local only")

        # Test "in sync"
        self.sync_engine.push(user_id)
        self.assertEqual(self.sync_engine.get_sync_status(user_id), "in sync")

        # Test "conflict"
        profile.add_command_to_history("new command")
        self.local_storage.save(user_id, dataclasses.asdict(profile))
        self.assertEqual(self.sync_engine.get_sync_status(user_id), "conflict")

        # Test "remote only"
        os.remove(self.test_user_data_dir / f"{user_id}.json")
        self.assertEqual(self.sync_engine.get_sync_status(user_id), "remote only")


if __name__ == '__main__':
    unittest.main()
