import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from typing import List, Dict

metadata = sqlalchemy.MetaData()

change_events_table = sqlalchemy.Table(
    "change_events",
    metadata,
    sqlalchemy.Column("event_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("time", sqlalchemy.DateTime(timezone=True), server_default=func.now(), nullable=False),
    sqlalchemy.Column("source_url", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("event_type", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("details", JSONB, nullable=False),
    sqlalchemy.Column("metadata", JSONB),
)

class TimeseriesDBClient:
    """
    A client to interact with the timeseries database for storing change events.
    """
    def __init__(self, engine):
        self.engine = engine

    async def save_events(self, events: List[Dict]):
        """Saves a list of ChangeEvent dictionaries to the database."""
        if not events:
            return

        # Note: The 'events' are expected to be dicts matching the table structure.
        # The ChangeEvent TypedDict from the delta_detector should be converted to this.
        stmt = change_events_table.insert()
        async with self.engine.connect() as conn:
            await conn.execute(stmt, events)
            await conn.commit()
        print(f"Saved {len(events)} events to timeseries DB.")

async def create_tables(engine):
    """
    Function to create the tables defined in the metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    print("Timeseries tables created (if they didn't exist).")
