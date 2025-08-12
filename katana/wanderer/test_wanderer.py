import unittest
import os
from pathlib import Path
import yaml
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add the project root to the path to allow direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from katana.wanderer.guardian import GuardianProxy
from katana.wanderer.parser import extract_main_content
from katana.wanderer.storage.graph_archive import AstrographicsClient
from katana.wanderer.storage.frontier_queue import FrontierQueueClient
from katana.wanderer.navigation.assessor import LinkAssessor

# A helper to run async tests
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

class TestWandererComponents(unittest.TestCase):

    def setUp(self):
        """Set up a controlled test environment."""
        self.test_protocol_path = "test_safety_protocol.yml"
        self.test_config = {
            'network_rules': {'user_agent': "TestWanderer/1.0"},
            'content_rules': {'forbidden_file_types': ['.exe']},
            'ethical_rules': {'no_denial_of_service': True}
        }
        with open(self.test_protocol_path, 'w') as f:
            yaml.dump(self.test_config, f)

    def tearDown(self):
        """Clean up the environment after tests."""
        if os.path.exists(self.test_protocol_path):
            os.remove(self.test_protocol_path)

    def test_guardian_loads_protocol_correctly(self):
        guardian = GuardianProxy(protocol_path=self.test_protocol_path)
        self.assertEqual(guardian.network_rules['user_agent'], "TestWanderer/1.0")
        print(f"\nGuardian User-Agent check PASSED.")

    def test_parser_extracts_main_content(self):
        sample_html = "<html><head><title>Test Title</title></head><body><main><h1>Main Content</h1><p>Some text.</p></main><footer>Ignore this</footer></body></html>"
        extracted_data = extract_main_content(sample_html)
        self.assertEqual(extracted_data['title'], "Test Title")
        self.assertIn("Main Content", extracted_data['content_text'])
        self.assertNotIn("Ignore this", extracted_data['content_text'])
        print(f"Parser main content extraction check PASSED.")

    @async_test
    @patch('katana.wanderer.storage.graph_archive.AsyncGraphDatabase')
    async def test_astrographics_client_add_page(self, mock_db):
        """Verify AstrographicsClient calls the correct transaction function for adding a page."""
        # The driver method returns a synchronous mock object
        mock_driver = MagicMock()
        mock_db.driver.return_value = mock_driver

        # The session() method on the driver returns an async context manager
        mock_async_session_cm = AsyncMock()
        mock_driver.session.return_value = mock_async_session_cm

        # The context manager, when entered, returns the actual session instance
        mock_session_instance = AsyncMock()
        mock_async_session_cm.__aenter__.return_value = mock_session_instance

        client = AstrographicsClient("uri", "user", "pass")

        test_url = "http://example.com"
        test_title = "Example"
        test_hash = "12345"

        await client.add_or_update_page(test_url, test_title, test_hash)

        mock_driver.session.assert_called_once()
        mock_session_instance.execute_write.assert_called_once()

        call_args = mock_session_instance.execute_write.call_args
        self.assertEqual(call_args[0][0], client._create_or_update_page_tx)
        self.assertEqual(call_args.kwargs['url'], test_url)

        print(f"AstrographicsClient add_or_update_page check PASSED.")

    @async_test
    @patch('katana.wanderer.storage.frontier_queue.redis.Redis')
    async def test_frontier_queue_client_add_url(self, mock_redis_class):
        """Verify FrontierQueueClient calls redis.zadd correctly."""
        mock_redis_instance = AsyncMock()
        mock_redis_class.return_value = mock_redis_instance

        client = FrontierQueueClient()
        test_url = "http://next.com"
        test_priority = 0.9

        await client.add_url(test_url, test_priority)

        mock_redis_instance.zadd.assert_called_once_with(client.queue_name, {test_url: test_priority})
        print(f"FrontierQueueClient add_url check PASSED.")

    @async_test
    @patch('katana.wanderer.storage.frontier_queue.redis.Redis')
    async def test_frontier_queue_client_get_next_url(self, mock_redis_class):
        """Verify FrontierQueueClient calls redis.zpopmax and returns the URL."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.zpopmax.return_value = [("http://pop.com", -0.9)]
        mock_redis_class.return_value = mock_redis_instance

        client = FrontierQueueClient()
        next_url = await client.get_next_url()

        mock_redis_instance.zpopmax.assert_called_once_with(client.queue_name)
        self.assertEqual(next_url, "http://pop.com")
        print(f"FrontierQueueClient get_next_url check PASSED.")

    @async_test
    async def test_link_assessor_formats_prompt_correctly(self):
        """Verify LinkAssessor formats the LLM prompt correctly."""
        assessor = LinkAssessor()
        mission = "Find AI research papers"
        links = [{"url": "http://ai.com/paper.pdf", "anchor": "Read paper", "context": "Our new paper..."}]

        result = await assessor.assess(links, mission)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], links[0]['url'])
        self.assertEqual(result[0]['relevance'], 0.85)

        formatted_prompt = assessor._SYSTEM_PROMPT_TEMPLATE.format(
            mission_goal=mission,
            links_data=str(links)
        )
        self.assertIn(mission, formatted_prompt)
        self.assertIn(links[0]['url'], formatted_prompt)
        print(f"LinkAssessor check PASSED.")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
