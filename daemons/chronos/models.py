from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TickerData(BaseModel):
    """
    Pydantic model for validating incoming ticker data from the Coinbase WebSocket feed.
    """
    type: str
    sequence: int
    product_id: str
    price: float
    open_24h: float
    volume_24h: float
    low_24h: float
    high_24h: float
    volume_30d: float
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    side: Optional[str] = None
    time: datetime
    trade_id: int
    last_size: Optional[float] = None
