import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from katana.modules import status_logger


def test_log_status(capsys):
    status_logger.log_status("Test")
    captured = capsys.readouterr()
    assert "Test" in captured.out
