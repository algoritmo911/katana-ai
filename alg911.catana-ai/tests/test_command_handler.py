import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from katana.modules.command_handler import handle


def test_handle_known_command():
    result = handle("status")
    assert result == "Status: OK"
