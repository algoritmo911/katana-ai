import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from katana.modules import command_handler


def test_handle_known_command():
    result = command_handler.handle("status")
    assert result == "Status: OK"
