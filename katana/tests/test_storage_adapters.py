import unittest
import os
import json
import shutil
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from katana.adapters.local_file_adapter import LocalFileAdapter
from katana.adapters.mock_cloud_adapter import MockCloudAdapter

class TestStorageAdapters(unittest.TestCase):

    def setUp(self):
        self.test_user_data_dir = Path("test_user_data_temp_dir")
        self.test_user_data_dir.mkdir(parents=True, exist_ok=True)
        self.remote_db_file = Path("test_remote_db.json")

        self.local_adapter = LocalFileAdapter()
        self.local_adapter.USER_DATA_DIR = self.test_user_data_dir

        self.mock_cloud_adapter = MockCloudAdapter()
        self.mock_cloud_adapter.REMOTE_DB_FILE = self.remote_db_file

    def tearDown(self):
        if self.test_user_data_dir.exists():
            shutil.rmtree(self.test_user_data_dir)
        if self.remote_db_file.exists():
            os.remove(self.remote_db_file)

    def test_local_file_adapter(self):
        user_id = 123
        data = {"test": "data"}
        self.local_adapter.save(user_id, data)
        loaded_data = self.local_adapter.load(user_id)
        self.assertEqual(data, loaded_data)

    def test_mock_cloud_adapter(self):
        user_id = 456
        data = {"test": "data"}
        self.mock_cloud_adapter.save(user_id, data)
        loaded_data = self.mock_cloud_adapter.load(user_id)
        self.assertEqual(data, loaded_data)

if __name__ == '__main__':
    unittest.main()
