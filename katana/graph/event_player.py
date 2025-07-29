from typing import List
from .command_graph import CommandGraph
from .events import GraphEvent
from .command import Command

class EventPlayer:
    @staticmethod
    def replay(events: List[GraphEvent]) -> CommandGraph:
        graph = CommandGraph()
        for event in events:
            if event.type == "ADD_NODE":
                command = Command.from_dict(event.payload)
                graph.add_command(command)
            elif event.type == "REMOVE_NODE":
                graph.remove_command(event.payload["command_id"])
            elif event.type == "UPDATE_STATUS":
                graph.update_command_status(event.payload["command_id"], event.payload["status"])
        return graph

    @staticmethod
    def undo(events: List[GraphEvent], steps: int) -> CommandGraph:
        # This is a simplified implementation. A more robust implementation would
        # require a more sophisticated way to reverse events.
        if steps > len(events):
            raise ValueError("Cannot undo more steps than there are events.")

        relevant_events = events[:-steps]
        return EventPlayer.replay(relevant_events)
