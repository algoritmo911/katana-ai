import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add the project root to the path to allow direct imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from katana.wanderer.agent import WandererAgent
from katana.wanderer.crawler import AsyncCrawler
from katana.wanderer.parser import extract_main_content
from katana.wanderer.storage.graph_archive import AstrographicsClient
from katana.wanderer.storage.frontier_queue import FrontierQueueClient
from katana.wanderer.storage.knowledge_queue import KnowledgeQueueClient
from katana.wanderer.storage.timeseries_db import TimeseriesDBClient
from katana.wanderer.navigation.assessor import LinkAssessor
from katana.wanderer.logic.delta_detector import DeltaDetector, ChangeEvent

def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

class TestWandererE2EWithKairos(unittest.TestCase):
    @async_test
    async def test_kairos_e2e_cycle_with_change_detection(self):
        """E2E test for the WandererAgent with Kairos temporal logic."""
        # 1. Mock Web Environment
        mock_website = {
            "http://example.com/pageA": "<html><title>A v1</title><body>Version 1 of A</body></html>",
            "http://example.com/pageA_v2": "<html><title>A v2</title><body>Version 2 of A</body></html>",
        }
        mock_crawler = AsyncMock(spec=AsyncCrawler)
        async def mock_fetch(url):
             # The agent will crawl the same logical page, but our mock returns different content
            if url == "http://example.com/pageA":
                if mock_crawler.fetch.call_count == 1:
                    return mock_website["http://example.com/pageA"]
                else:
                    return mock_website["http://example.com/pageA_v2"]
            return ""
        mock_crawler.fetch.side_effect = mock_fetch

        # 2. Mock Dependencies
        mock_frontier = AsyncMock(spec=FrontierQueueClient)
        mock_archive = AsyncMock(spec=AstrographicsClient)
        mock_knowledge = AsyncMock(spec=KnowledgeQueueClient)
        mock_assessor = AsyncMock(spec=LinkAssessor)
        mock_ts_db = AsyncMock(spec=TimeseriesDBClient)
        mock_detector = AsyncMock(spec=DeltaDetector)

        # 3. Configure Mock Behaviors
        frontier_urls = ["http://example.com/pageA", "http://example.com/pageA"] # Re-visit the same URL
        mock_frontier.get_next_url.side_effect = lambda: (frontier_urls.pop(0) if frontier_urls else None)

        page_data = {}
        async def get_page_by_url(url): return page_data.get(url)
        async def add_or_update_page(url, title, hash, text): page_data[url] = {'url': url, 'title': title, 'content_hash': hash, 'content_text': text}
        async def get_content_by_hash(hash):
            for page in page_data.values():
                if page['content_hash'] == hash: return page['content_text']
            return None

        mock_archive.get_page_by_url.side_effect = get_page_by_url
        mock_archive.add_or_update_page.side_effect = add_or_update_page
        mock_archive.get_content_by_hash.side_effect = get_content_by_hash

        change_event = ChangeEvent(event_type="CONTENT_MODIFIED", source_url="http://example.com/pageA", details={})
        mock_detector.detect_changes.return_value = [change_event]

        # 4. Initialize and Run Agent
        agent = WandererAgent(
            mission_goal="Detect changes",
            frontier_queue=mock_frontier,
            graph_archive=mock_archive,
            knowledge_queue=mock_knowledge,
            timeseries_db=mock_ts_db,
            delta_detector=mock_detector,
            crawler=mock_crawler,
            link_assessor=AsyncMock(), # Not relevant for this test
            parser_func=lambda html, base_url: {"content_text": BeautifulSoup(html, 'html.parser').body.get_text(), "title": BeautifulSoup(html, 'html.parser').title.string, "links": []}
        )

        await agent.step() # Processes pageA v1
        await agent.step() # Re-processes pageA, gets v2, detects change

        # 5. Assertions
        self.assertEqual(mock_crawler.fetch.call_count, 2)
        mock_detector.detect_changes.assert_called_once()
        mock_ts_db.save_events.assert_called_once_with([change_event])
        agent.event_bus.publish.assert_called_once_with("change-events", change_event)

        # Verify the graph was updated to the latest version
        self.assertEqual(page_data["http://example.com/pageA"]['title'], "A v2")

        print("\nE2E Test: Kairos temporal cycle check PASSED.")

# Need to import BeautifulSoup for the E2E test lambda
from bs4 import BeautifulSoup

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
