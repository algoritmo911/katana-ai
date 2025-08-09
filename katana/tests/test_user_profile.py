import unittest
import os
import json
from pathlib import Path
import shutil
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from katana.core.user_profile import UserProfile
import dataclasses

class TestUserProfile(unittest.TestCase):

    def test_create_new_profile(self):
        user_id = 123
        profile = UserProfile(user_id)
        self.assertEqual(profile.user_id, user_id)
        self.assertEqual(profile.command_history, [])
        self.assertEqual(profile.preferences, {})
        self.assertIsNone(profile.last_seen)

    def test_add_command_to_history(self):
        user_id = 789
        profile = UserProfile(user_id)
        profile.add_command_to_history("command 1")
        profile.add_command_to_history("command 2")
        self.assertEqual(len(profile.command_history), 2)
        self.assertEqual(profile.command_history[0]['command'], "command 1")
        self.assertEqual(profile.command_history[1]['command'], "command 2")

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

if __name__ == '__main__':
    unittest.main()
