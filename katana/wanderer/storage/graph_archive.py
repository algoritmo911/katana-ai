from neo4j import AsyncGraphDatabase

class AstrographicsClient:
    """
    Клиент для взаимодействия с Neo4j, нашим Астрографическим Архивом.
    Хранит карту исследованной вселенной.
    """
    def __init__(self, uri, user, password):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def add_or_update_page(self, url: str, title: str, content_hash: str):
        """Добавляет или обновляет узел страницы в графе."""
        async with self.driver.session() as session:
            await session.execute_write(
                self._create_or_update_page_tx,
                url=url, title=title, content_hash=content_hash
            )

    @staticmethod
    async def _create_or_update_page_tx(tx, url, title, content_hash):
        # MERGE ищет узел по url. Если находит - обновляет, если нет - создает. Атомарно.
        query = (
            "MERGE (p:Page {url: $url}) "
            "ON CREATE SET p.title = $title, p.content_hash = $content_hash, p.first_visited = timestamp() "
            "ON MATCH SET p.title = $title, p.content_hash = $content_hash, p.last_visited = timestamp()"
        )
        tx.run(query, url=url, title=title, content_hash=content_hash)

    async def add_link(self, source_url: str, target_url: str):
        """Создает отношение LINKS_TO между двумя узлами страниц."""
        async with self.driver.session() as session:
            await session.execute_write(self._create_link_tx, source_url, target_url)

    @staticmethod
    async def _create_link_tx(tx, source_url, target_url):
        # Создаем связь между двумя существующими страницами
        query = (
            "MATCH (source:Page {url: $source_url}) "
            "MATCH (target:Page {url: $target_url}) "
            "MERGE (source)-[:LINKS_TO]->(target)"
        )
        tx.run(query, source_url=source_url, target_url=target_url)

    async def page_exists(self, url: str) -> bool:
        """Проверяет, существует ли страница в архиве."""
        async with self.driver.session() as session:
            result = await session.execute_read(self._check_page_exists_tx, url)
            return result

    @staticmethod
    async def _check_page_exists_tx(tx, url) -> bool:
        query = "MATCH (p:Page {url: $url}) RETURN count(p) > 0 AS exists"
        result = tx.run(query, url=url)
        record = result.single()
        return record["exists"] if record else False
