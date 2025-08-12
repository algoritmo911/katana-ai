import asyncio
import hashlib
from typing import Callable

from katana.wanderer.storage.frontier_queue import FrontierQueueClient
from katana.wanderer.storage.graph_archive import AstrographicsClient
from katana.wanderer.crawler import AsyncCrawler
from katana.wanderer.navigation.assessor import LinkAssessor
from katana.wanderer.parser import extract_main_content
from katana.wanderer.storage.knowledge_queue import KnowledgeQueueClient

class WandererAgent:
    def __init__(
        self,
        mission_goal: str,
        frontier_queue: FrontierQueueClient,
        graph_archive: AstrographicsClient,
        knowledge_queue: KnowledgeQueueClient,
        crawler: AsyncCrawler,
        link_assessor: LinkAssessor,
        parser_func: Callable = extract_main_content,
    ):
        self.mission_goal = mission_goal
        self.frontier_queue = frontier_queue
        self.graph_archive = graph_archive
        self.knowledge_queue = knowledge_queue
        self.crawler = crawler
        self.parser = parser_func
        self.link_assessor = link_assessor
        self.RELEVANCE_THRESHOLD = 0.5

    async def step(self) -> bool:
        """
        Processes a single URL from the frontier. Returns True if work was done, False otherwise.
        """
        url_to_crawl = await self.frontier_queue.get_next_url()

        if not url_to_crawl:
            print("WandererAgent: Frontier is empty.")
            return False

        print(f"WandererAgent: Processing URL: {url_to_crawl}")

        if await self.graph_archive.page_exists(url_to_crawl):
            print(f"WandererAgent: URL {url_to_crawl} already visited. Skipping.")
            return True # Still counts as work done

        try:
            html_content = await self.crawler.fetch(url_to_crawl)
            if not html_content:
                return True

            parsed_data = self.parser(html_content, base_url=url_to_crawl)
            content_text = parsed_data.get("content_text", "")
            title = parsed_data.get("title", "")
            links = parsed_data.get("links", [])

            if content_text:
                await self.knowledge_queue.submit_content(url_to_crawl, content_text)

            assessed_links = await self.link_assessor.assess(links, self.mission_goal)

            for link in assessed_links:
                if link.get('relevance', 0.0) > self.RELEVANCE_THRESHOLD:
                    await self.frontier_queue.add_url(link['url'], link['relevance'])

            content_hash = self._calculate_hash(content_text)
            await self.graph_archive.add_or_update_page(url_to_crawl, title, content_hash)
            for link in links:
                await self.graph_archive.add_link(url_to_crawl, link['url'])

        except Exception as e:
            print(f"WandererAgent: Error processing {url_to_crawl}: {e}")

        return True

    def _calculate_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
