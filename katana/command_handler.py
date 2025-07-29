from .event_store.event_store import EventStore

class CommandHandler:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def create_command(self, command_id: str, command_type: str, args: dict):
        # In a real implementation, we would validate the command here.
        self.event_store.append(
            event_type="COMMAND_CREATED",
            aggregate_id=command_id,
            payload={"type": command_type, "args": args},
        )

    def start_command(self, command_id: str):
        self.event_store.append(
            event_type="COMMAND_STARTED",
            aggregate_id=command_id,
            payload={},
        )

    def complete_command(self, command_id: str):
        self.event_store.append(
            event_type="COMMAND_COMPLETED",
            aggregate_id=command_id,
            payload={},
        )

    def fail_command(self, command_id: str):
        self.event_store.append(
            event_type="COMMAND_FAILED",
            aggregate_id=command_id,
            payload={},
        )

    def create_child_command(self, child_id: str, parent_id: str, command_type: str, args: dict):
        self.event_store.append(
            event_type="CHILD_COMMAND_CREATED",
            aggregate_id=child_id,
            payload={"parent_id": parent_id, "type": command_type, "args": args},
        )
