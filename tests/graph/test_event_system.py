import unittest
import os
import shutil
from datetime import datetime
from katana.graph.command import Command
from katana.graph.command_graph import CommandGraph
from katana.graph.events import GraphEvent, EventLog
from katana.graph.event_player import EventPlayer

class TestEventSystem(unittest.TestCase):

    def setUp(self):
        self.event_log_path = "test_event_log.jsonl"
        self.event_log = EventLog(self.event_log_path)
        self.graph = CommandGraph(event_log=self.event_log)

    def tearDown(self):
        if os.path.exists(self.event_log_path):
            os.remove(self.event_log_path)

    def test_log_and_replay_events(self):
        # Add a command, which should log an ADD_NODE event
        cmd1_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        cmd1 = Command(cmd1_data)
        self.graph.add_command(cmd1)

        # Add another command with a parent, which should log ADD_NODE and ADD_EDGE events
        cmd2_data = {"id": "2", "type": "cmd2", "module": "test", "args": {}, "parent_id": "1"}
        cmd2 = Command(cmd2_data, parent_id="1")
        self.graph.add_command(cmd2)

        # Update a command's status, which should log an UPDATE_STATUS event
        self.graph.update_command_status("1", "DONE")

        # Read the events from the log
        events = self.event_log.read_events()
        self.assertEqual(len(events), 4) # ADD_NODE, ADD_NODE, ADD_EDGE, UPDATE_STATUS

        # Replay the events and check the resulting graph
        replayed_graph = EventPlayer.replay(events)
        self.assertEqual(len(replayed_graph._commands), 2)
        self.assertEqual(replayed_graph.get_command("1").status, "DONE")
        self.assertEqual(replayed_graph.get_command("2").parent_id, "1")

    def test_undo_events(self):
        # Add some commands
        cmd1_data = {"id": "1", "type": "cmd1", "module": "test", "args": {}}
        cmd1 = Command(cmd1_data)
        self.graph.add_command(cmd1)
        cmd2_data = {"id": "2", "type": "cmd2", "module": "test", "args": {}, "parent_id": "1"}
        cmd2 = Command(cmd2_data, parent_id="1")
        self.graph.add_command(cmd2)

        # Undo the last two events (ADD_NODE for cmd2 and ADD_EDGE)
        events = self.event_log.read_events()
        undone_graph = EventPlayer.undo(events, 2)

        # Check the resulting graph
        self.assertEqual(len(undone_graph._commands), 1)
        self.assertIsNone(undone_graph.get_command("2"))

if __name__ == '__main__':
    unittest.main()
