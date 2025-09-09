import logging
import psycopg2
from .models import TickerData

# Configure logging
logger = logging.getLogger(__name__)

# --- QuestDB Configuration ---
QUESTDB_CONN_STRING = "user=admin password=quest host=localhost port=8812 dbname=qdb"

def get_db_connection():
    """Establishes and returns a connection to the QuestDB database."""
    try:
        return psycopg2.connect(QUESTDB_CONN_STRING)
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to QuestDB: {e}")
        return None

def create_tickers_table(conn):
    """Creates the 'tickers' table in QuestDB if it doesn't exist."""
    if conn is None:
        logger.error("Cannot create table: no database connection.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickers (
                    product_id SYMBOL,
                    price DOUBLE,
                    volume_24h DOUBLE,
                    ts TIMESTAMP
                ) TIMESTAMP(ts) PARTITION BY DAY;
            """)
        conn.commit()
        logger.info("Table 'tickers' created or already exists.")
    except psycopg2.Error as e:
        logger.error(f"Failed to create 'tickers' table: {e}")
        conn.rollback()

def insert_ticker_data(conn, ticker: TickerData):
    """Inserts a single ticker data record into the 'tickers' table."""
    if conn is None:
        logger.error("Cannot insert data: no database connection.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tickers (product_id, price, volume_24h, ts)
                VALUES (%s, %s, %s, %s);
                """,
                (ticker.product_id, ticker.price, ticker.volume_24h, ticker.time)
            )
        conn.commit()
        logger.info(f"Inserted ticker data for {ticker.product_id} at {ticker.time}")
    except psycopg2.Error as e:
        logger.error(f"Failed to insert ticker data: {e}")
        conn.rollback()
