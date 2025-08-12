from neo4j import AsyncGraphDatabase, Record
from typing import Dict, Optional

class AstrographicsClient:
    """
    Client for interacting with Neo4j, our Astrographics Archive.
    """
    def __init__(self, uri, user, password):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def add_or_update_page(self, url: str, title: str, content_hash: str, content_text: str):
        """Adds or updates a page node, now including content_text."""
        async with self.driver.session() as session:
            await session.execute_write(
                self._create_or_update_page_tx,
                url=url, title=title, content_hash=content_hash, content_text=content_text
            )

    @staticmethod
    async def _create_or_update_page_tx(tx, url, title, content_hash, content_text):
        query = (
            "MERGE (p:Page {url: $url}) "
            "ON CREATE SET p.title = $title, p.content_hash = $content_hash, p.content_text = $content_text, p.first_visited = timestamp() "
            "ON MATCH SET p.title = $title, p.content_hash = $content_hash, p.content_text = $content_text, p.last_visited = timestamp()"
        )
        tx.run(query, url=url, title=title, content_hash=content_hash, content_text=content_text)

    async def add_link(self, source_url: str, target_url: str):
        async with self.driver.session() as session:
            await session.execute_write(self._create_link_tx, source_url, target_url)

    @staticmethod
    async def _create_link_tx(tx, source_url, target_url):
        query = (
            "MATCH (source:Page {url: $source_url}), (target:Page {url: $target_url}) "
            "MERGE (source)-[:LINKS_TO]->(target)"
        )
        tx.run(query, source_url=source_url, target_url=target_url)

    async def get_page_by_url(self, url: str) -> Optional[Dict]:
        """Fetches a page node's data by its URL."""
        async with self.driver.session() as session:
            result = await session.execute_read(self._get_page_by_url_tx, url)
            return result

    @staticmethod
    async def _get_page_by_url_tx(tx, url) -> Optional[Dict]:
        query = "MATCH (p:Page {url: $url}) RETURN p"
        result = tx.run(query, url=url)
        record: Optional[Record] = result.single()
        if record and record["p"]:
            return dict(record["p"])
        return None

    # This method is now simplified as content is stored on the node
    async def get_content_by_hash(self, content_hash: str) -> Optional[str]:
        """Retrieves content_text from a node by its content_hash."""
        async with self.driver.session() as session:
            result = await session.execute_read(self._get_content_by_hash_tx, content_hash)
            return result

    @staticmethod
    async def _get_content_by_hash_tx(tx, content_hash: str) -> Optional[str]:
        query = "MATCH (p:Page {content_hash: $content_hash}) RETURN p.content_text AS content"
        result = tx.run(query, content_hash=content_hash)
        record = result.single()
        return record["content"] if record else None
