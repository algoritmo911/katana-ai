import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
import subprocess

# Add the katana directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from self_check import run_all, _check_env_file, _check_pyc, _check_redis, _check_telegram, _check_dependencies, _check_project_structure, _check_logs, _check_tests

class TestSelfCheck(unittest.TestCase):

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.exists', return_value=True)
    def test_check_env_file_exists(self, mock_exists, mock_open):
        try:
            _check_env_file()
        except FileNotFoundError:
            self.fail("_check_env_file() raised FileNotFoundError unexpectedly!")

    def test_check_env_file_not_exists(self):
        if os.path.exists('.env'):
            os.remove('.env')
        with self.assertRaises(FileNotFoundError):
            _check_env_file()
        open('.env', 'w').close()

    @patch('pathlib.Path.rglob', return_value=[])
    def test_check_pyc_no_pyc_files(self, mock_rglob):
        try:
            _check_pyc()
        except RuntimeError:
            self.fail("_check_pyc() raised RuntimeError unexpectedly!")

    @patch('pathlib.Path.rglob', return_value=['file.pyc'])
    def test_check_pyc_with_pyc_files(self, mock_rglob):
        with self.assertRaises(RuntimeError):
            _check_pyc()

    @patch('redis.Redis.from_url')
    @patch.dict(os.environ, {"REDIS_URL": "redis://localhost"})
    def test_check_redis_success(self, mock_redis):
        mock_redis.return_value.ping.return_value = True
        try:
            _check_redis()
        except RuntimeError:
            self.fail("_check_redis() raised RuntimeError unexpectedly!")

    @patch('redis.Redis.from_url')
    @patch.dict(os.environ, {"REDIS_URL": "redis://localhost"})
    def test_check_redis_failure(self, mock_redis):
        mock_redis.return_value.ping.side_effect = Exception("Connection error")
        with self.assertRaises(RuntimeError):
            _check_redis()

    @patch('telegram.Bot')
    @patch.dict(os.environ, {"TELEGRAM_TOKEN": "test_token"})
    def test_check_telegram_success(self, mock_bot):
        mock_bot.return_value.get_me.return_value = {}
        try:
            _check_telegram()
        except RuntimeError:
            self.fail("_check_telegram() raised RuntimeError unexpectedly!")

    @patch('telegram.Bot')
    @patch.dict(os.environ, {"TELEGRAM_TOKEN": "test_token"})
    def test_check_telegram_failure(self, mock_bot):
        mock_bot.return_value.get_me.side_effect = Exception("Invalid token")
        with self.assertRaises(RuntimeError):
            _check_telegram()

    @patch('subprocess.run')
    def test_check_dependencies_success(self, mock_run):
        mock_run.return_value = MagicMock(check=True, capture_output=True, text=True)
        try:
            _check_dependencies()
        except RuntimeError:
            self.fail("_check_dependencies() raised RuntimeError unexpectedly!")

    @patch('subprocess.run')
    def test_check_dependencies_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", "output")
        with self.assertRaises(RuntimeError):
            _check_dependencies()

    @patch('pathlib.Path.is_dir', return_value=True)
    def test_check_project_structure_success(self, mock_is_dir):
        try:
            _check_project_structure()
        except NotADirectoryError:
            self.fail("_check_project_structure() raised NotADirectoryError unexpectedly!")

    @patch('pathlib.Path.is_dir', return_value=False)
    def test_check_project_structure_failure(self, mock_is_dir):
        with self.assertRaises(NotADirectoryError):
            _check_project_structure()

    @patch('pathlib.Path.is_dir', return_value=True)
    def test_check_logs_success(self, mock_is_dir):
        try:
            _check_logs()
        except NotADirectoryError:
            self.fail("_check_logs() raised NotADirectoryError unexpectedly!")

    @patch('pathlib.Path.is_dir', return_value=False)
    def test_check_logs_failure(self, mock_is_dir):
        with self.assertRaises(NotADirectoryError):
            _check_logs()

    @patch('subprocess.run')
    def test_check_tests_success(self, mock_run):
        mock_run.return_value = MagicMock(check=True, capture_output=True, text=True)
        try:
            _check_tests()
        except RuntimeError:
            self.fail("_check_tests() raised RuntimeError unexpectedly!")

    @patch('subprocess.run')
    def test_check_tests_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", "output")
        with self.assertRaises(RuntimeError):
            _check_tests()

    @patch('self_check.sys.exit')
    @patch('self_check.log')
    @patch('self_check._check_env_file', side_effect=FileNotFoundError)
    def test_run_all_critical_error(self, mock_check_env, mock_log, mock_exit):
        run_all()
        mock_exit.assert_called_with(1)

if __name__ == '__main__':
    unittest.main()
