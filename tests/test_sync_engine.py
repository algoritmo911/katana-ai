import unittest
import os
import json
import shutil
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.sync_engine import push_profile_to_cloud, pull_profile_from_cloud, get_sync_status
from core.user_profile import UserProfile

class TestSyncEngine(unittest.TestCase):

    def setUp(self):
        self.test_user_data_dir = Path("test_user_data_temp_dir")
        self.test_user_data_dir.mkdir(parents=True, exist_ok=True)
        self.remote_db_file = Path("test_remote_db.json")

        self.user_data_dir_patcher = unittest.mock.patch('core.sync_engine.USER_DATA_DIR', self.test_user_data_dir)
        self.remote_db_patcher = unittest.mock.patch('core.sync_engine.REMOTE_DB_FILE', self.remote_db_file)

        self.user_data_dir_patcher.start()
        self.remote_db_patcher.start()

    def tearDown(self):
        self.user_data_dir_patcher.stop()
        self.remote_db_patcher.stop()
        if self.test_user_data_dir.exists():
            shutil.rmtree(self.test_user_data_dir)
        if self.remote_db_file.exists():
            os.remove(self.remote_db_file)

    def test_push_profile_to_cloud(self):
        user_id = 123
        profile = UserProfile(user_id)
        profile.profile_path = self.test_user_data_dir / f"{user_id}.json"
        profile.add_command_to_history("test command")
        profile.save()

        push_profile_to_cloud(user_id)

        self.assertTrue(self.remote_db_file.exists())
        with open(self.remote_db_file, 'r') as f:
            remote_data = json.load(f)

        self.assertIn(str(user_id), remote_data)
        self.assertEqual(remote_data[str(user_id)]['data']['user_id'], user_id)
        self.assertIsNotNone(remote_data[str(user_id)]['hash'])

    def test_pull_profile_from_cloud(self):
        user_id = 456
        profile_data = {"user_id": user_id, "command_history": [{"command": "remote command", "timestamp": "now"}]}

        with open(self.remote_db_file, 'w') as f:
            json.dump({str(user_id): {"data": profile_data, "hash": "somehash"}}, f)

        pull_profile_from_cloud(user_id)

        local_profile_path = self.test_user_data_dir / f"{user_id}.json"
        self.assertTrue(local_profile_path.exists())
        with open(local_profile_path, 'r') as f:
            local_data = json.load(f)

        self.assertEqual(local_data['command_history'][0]['command'], "remote command")

    def test_get_sync_status(self):
        user_id = 789

        # Test "not found"
        self.assertEqual(get_sync_status(user_id), "not found")

        # Test "local only"
        profile = UserProfile(user_id)
        profile.profile_path = self.test_user_data_dir / f"{user_id}.json"
        profile.save()
        self.assertEqual(get_sync_status(user_id), "local only")

        # Test "in sync"
        push_profile_to_cloud(user_id)
        self.assertEqual(get_sync_status(user_id), "in sync")

        # Test "conflict"
        profile.add_command_to_history("new command")
        profile.save()
        self.assertEqual(get_sync_status(user_id), "conflict")

        # Test "remote only"
        os.remove(profile.profile_path)
        self.assertEqual(get_sync_status(user_id), "remote only")


if __name__ == '__main__':
    unittest.main()
