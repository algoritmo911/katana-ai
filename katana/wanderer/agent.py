import asyncio
import hashlib
from typing import Callable, Dict
from unittest.mock import AsyncMock

from katana.wanderer.storage.frontier_queue import FrontierQueueClient
from katana.wanderer.storage.graph_archive import AstrographicsClient
from katana.wanderer.storage.timeseries_db import TimeseriesDBClient # Assuming this client exists
from katana.wanderer.logic.delta_detector import DeltaDetector
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
        timeseries_db: TimeseriesDBClient, # New Kairos dependency
        delta_detector: DeltaDetector,   # New Kairos dependency
        crawler: AsyncCrawler,
        link_assessor: LinkAssessor,
        parser_func: Callable = extract_main_content,
    ):
        self.mission_goal = mission_goal
        self.frontier_queue = frontier_queue
        self.graph_archive = graph_archive
        self.knowledge_queue = knowledge_queue
        self.timeseries_db = timeseries_db
        self.delta_detector = delta_detector
        self.crawler = crawler
        self.parser = parser_func
        self.link_assessor = link_assessor
        self.RELEVANCE_THRESHOLD = 0.5
        # This would be a real message bus client (e.g. redis pub/sub)
        self.event_bus = AsyncMock()

    async def step(self) -> bool:
        """
        Processes a single URL from the frontier, now with Kairos protocol integration.
        """
        url_to_crawl = await self.frontier_queue.get_next_url()
        if not url_to_crawl: return False

        print(f"WandererAgent: Processing URL: {url_to_crawl}")

        try:
            # Check existing state from graph archive
            # In a real system, this would return an object with page details
            existing_page_data: Dict = await self.graph_archive.get_page_by_url(url_to_crawl)

            # Crawl for new content
            new_html_content = await self.crawler.fetch(url_to_crawl)
            if not new_html_content: return True

            new_parsed_data = self.parser(new_html_content, base_url=url_to_crawl)
            new_content_text = new_parsed_data.get("content_text", "")
            new_content_hash = self._calculate_hash(new_content_text)

            # KAIROS PROTOCOL: DELTA DETECTION
            if existing_page_data and existing_page_data['content_hash'] != new_content_hash:
                print(f"WandererAgent: Change detected for {url_to_crawl}. Running Delta Detector.")
                # We need the old content to compare. A real system would fetch this from a content store (like S3)
                # using the old hash. We will mock this behavior in tests.
                old_content_text = await self.graph_archive.get_content_by_hash(existing_page_data['content_hash'])

                change_events = await self.delta_detector.detect_changes(url_to_crawl, old_content_text, new_content_text)

                if change_events:
                    # Save changes to timeseries DB and publish to event bus
                    await self.timeseries_db.save_events(change_events)
                    for event in change_events:
                        await self.event_bus.publish("change-events", event)

            # Standard processing continues
            title = new_parsed_data.get("title", "")
            links = new_parsed_data.get("links", [])

            if new_content_text:
                await self.knowledge_queue.submit_content(url_to_crawl, new_content_text)

            assessed_links = await self.link_assessor.assess(links, self.mission_goal)
            for link in assessed_links:
                if link.get('relevance', 0.0) > self.RELEVANCE_THRESHOLD:
                    await self.frontier_queue.add_url(link['url'], link['relevance'])

            # Update graph with the LATEST version
            await self.graph_archive.add_or_update_page(url_to_crawl, title, new_content_hash, new_content_text)
            for link in links:
                # In a real system, we might want to check if the target page exists before adding a link
                # For this prototype, we assume it will be created eventually.
                await self.graph_archive.add_link(url_to_crawl, link['url'])

        except Exception as e:
            print(f"WandererAgent: Error processing {url_to_crawl}: {e}")

        return True

    def _calculate_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

from unittest.mock import AsyncMock
