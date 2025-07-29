import unittest
import os
import json
from pathlib import Path
import shutil
from user_profile import UserProfile, get_user_profile

class TestUserProfile(unittest.TestCase):

    def setUp(self):
        self.test_user_data_dir = Path("test_user_data_temp_dir")
        self.test_user_data_dir.mkdir(parents=True, exist_ok=True)
        self.original_user_data_dir = 'user_profile.USER_DATA_DIR'
        self.user_data_dir_patcher = unittest.mock.patch(self.original_user_data_dir, self.test_user_data_dir)
        self.user_data_dir_patcher.start()

    def tearDown(self):
        self.user_data_dir_patcher.stop()
        if self.test_user_data_dir.exists():
            shutil.rmtree(self.test_user_data_dir)

    def test_create_new_profile(self):
        user_id = 123
        profile = UserProfile(user_id)
        self.assertEqual(profile.user_id, user_id)
        self.assertIsNone(profile.data['last_seen'])
        self.assertEqual(profile.data['command_history'], [])
        self.assertEqual(profile.data['preferences'], {})

    def test_save_and_load_profile(self):
        user_id = 456
        profile = UserProfile(user_id)
        profile.add_command_to_history("test command")
        profile.save()

        new_profile = UserProfile(user_id)
        self.assertEqual(new_profile.data['user_id'], user_id)
        self.assertEqual(len(new_profile.data['command_history']), 1)
        self.assertEqual(new_profile.data['command_history'][0]['command'], "test command")
        self.assertIsNotNone(new_profile.data['last_seen'])

    def test_add_command_to_history(self):
        user_id = 789
        profile = UserProfile(user_id)
        profile.add_command_to_history("command 1")
        profile.add_command_to_history("command 2")
        self.assertEqual(len(profile.data['command_history']), 2)
        self.assertEqual(profile.data['command_history'][0]['command'], "command 1")
        self.assertEqual(profile.data['command_history'][1]['command'], "command 2")

    def test_get_command_recommendations(self):
        user_id = 101
        profile = UserProfile(user_id)
        profile.add_command_to_history("ls -l")
        profile.add_command_to_history("ls -l")
        profile.add_command_to_history("df -h")
        profile.add_command_to_history("ls -l")
        profile.add_command_to_history("uptime")
        profile.add_command_to_history("df -h")

        recommendations = profile.get_command_recommendations(top_n=2)
        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0], "ls -l")
        self.assertEqual(recommendations[1], "df -h")

    def test_get_command_recommendations_empty_history(self):
        user_id = 112
        profile = UserProfile(user_id)
        recommendations = profile.get_command_recommendations()
        self.assertEqual(len(recommendations), 0)

    def test_get_user_profile_factory(self):
        user_id = 131
        profile = get_user_profile(user_id)
        self.assertIsInstance(profile, UserProfile)
        self.assertEqual(profile.user_id, user_id)

if __name__ == '__main__':
    unittest.main()
