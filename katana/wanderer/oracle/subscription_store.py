import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import List, Dict

metadata = sqlalchemy.MetaData()

oracle_subscriptions_table = sqlalchemy.Table(
    "oracle_subscriptions",
    metadata,
    sqlalchemy.Column("subscription_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("rule_definition", JSONB, nullable=False),
    sqlalchemy.Column("notification_channel", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True, nullable=False),
)

class SubscriptionStore:
    """
    Manages the persistence of Oracle subscriptions in the database.
    """
    def __init__(self, engine):
        self.engine = engine

    async def add_subscription(self, rule: Dict, channel: str) -> uuid.UUID:
        """Adds a new subscription and returns its ID."""
        stmt = oracle_subscriptions_table.insert().values(
            rule_definition=rule,
            notification_channel=channel
        ).returning(oracle_subscriptions_table.c.subscription_id)

        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            await conn.commit()
            return result.scalar_one()

    async def get_active_subscriptions(self) -> List[Dict]:
        """Retrieves all active subscription rules."""
        stmt = sqlalchemy.select(
            oracle_subscriptions_table.c.rule_definition,
            oracle_subscriptions_table.c.notification_channel
        ).where(oracle_subscriptions_table.c.is_active == True)

        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return result.mappings().all()
