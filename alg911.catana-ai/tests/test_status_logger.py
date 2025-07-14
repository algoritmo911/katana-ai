import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from katana.modules.status_logger import log_status


def test_log_status(capsys):
    log_status("Test")
    captured = capsys.readouterr()
    assert "Test" in captured.out
