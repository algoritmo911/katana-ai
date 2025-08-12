import unittest
import os
from pathlib import Path
import yaml
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add the project root to the path to allow direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from katana.wanderer.agent import WandererAgent
from katana.wanderer.crawler import AsyncCrawler
from katana.wanderer.parser import extract_main_content
from katana.wanderer.storage.graph_archive import AstrographicsClient
from katana.wanderer.storage.frontier_queue import FrontierQueueClient
from katana.wanderer.storage.knowledge_queue import KnowledgeQueueClient
from katana.wanderer.navigation.assessor import LinkAssessor

# A helper to run async tests
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

class TestWandererE2E(unittest.TestCase):
    @async_test
    async def test_full_exploration_cycle(self):
        """
        End-to-end test for the WandererAgent's exploration cycle.
        """
        # 1. Mock Web Environment
        mock_website = {
            "http://example.com/pageA": "<html><title>A</title><body><a href='http://example.com/pageB'>Go to B</a></body></html>",
            "http://example.com/pageB": "<html><title>B</title><body>The secret is here.</body></html>",
        }
        mock_crawler = AsyncMock(spec=AsyncCrawler)
        async def mock_fetch(url):
            return mock_website.get(url, "")
        mock_crawler.fetch.side_effect = mock_fetch

        # 2. Mock Dependencies
        mock_frontier = AsyncMock(spec=FrontierQueueClient)
        mock_archive = AsyncMock(spec=AstrographicsClient)
        mock_knowledge = AsyncMock(spec=KnowledgeQueueClient)
        mock_assessor = AsyncMock(spec=LinkAssessor)

        # 3. Configure Mock Behaviors
        frontier_urls = ["http://example.com/pageA"]
        async def get_next_url():
            return frontier_urls.pop(0) if frontier_urls else None
        async def add_url(url, priority):
            if priority > 0.5: # Only add relevant links
                frontier_urls.append(url)
        mock_frontier.get_next_url.side_effect = get_next_url
        mock_frontier.add_url.side_effect = add_url

        mock_archive.page_exists.return_value = False
        mock_assessor.assess.side_effect = lambda links, mission: [{'url': link['url'], 'relevance': 0.9} for link in links]

        # 4. Initialize and Run Agent
        agent = WandererAgent(
            mission_goal="Find the secret",
            frontier_queue=mock_frontier,
            graph_archive=mock_archive,
            knowledge_queue=mock_knowledge,
            crawler=mock_crawler,
            link_assessor=mock_assessor,
            parser_func=extract_main_content
        )

        # Run the agent for two steps
        await agent.step() # Processes pageA
        await agent.step() # Processes pageB

        # 5. Assertions
        self.assertEqual(mock_crawler.fetch.call_count, 2)
        mock_crawler.fetch.assert_any_call("http://example.com/pageA")
        mock_crawler.fetch.assert_any_call("http://example.com/pageB")

        mock_knowledge.submit_content.assert_any_call("http://example.com/pageB", "The secret is here.")

        mock_archive.add_or_update_page.assert_any_call("http://example.com/pageA", "A", unittest.mock.ANY)
        mock_archive.add_or_update_page.assert_any_call("http://example.com/pageB", "B", unittest.mock.ANY)

        mock_archive.add_link.assert_any_call("http://example.com/pageA", "http://example.com/pageB")

        print("\nE2E Test: Full exploration cycle check PASSED.")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
