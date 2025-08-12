import unittest
from src.agents.n8n_screenshot_analyzer import N8nScreenshotAnalyzer

class TestN8nScreenshotAnalyzer(unittest.TestCase):

    def setUp(self):
        # We can use a mock for the llm_client as it's not used in find_logical_errors
        self.analyzer = N8nScreenshotAnalyzer(llm_client=None)

    def test_finds_array_to_single_item_error(self):
        """
        Tests that the analyzer correctly identifies the logical error
        where a node producing an array is connected to a node expecting a single item.
        """
        # This mock workflow simulates the exact error scenario
        mock_workflow = {
            "nodes": [
                {"id": "1", "name": "Start", "type": "n8n-nodes-base.start"},
                {"id": "2", "name": "Get All Users", "type": "n8n-nodes-base.http-request"},
                {"id": "3", "name": "Send Telegram Message", "type": "n8n-nodes-base.telegram"}
            ],
            "connections": [
                {"source": "1", "target": "2"},
                {"source": "2", "target": "3"}
            ]
        }

        errors = self.analyzer.find_logical_errors(mock_workflow)

        # 1. Assert that exactly one error was found
        self.assertEqual(len(errors), 1)

        # 2. Assert that the error message is correct
        error_message = errors[0]
        self.assertIn("Logical error detected", error_message)
        self.assertIn("'Get All Users'", error_message)
        self.assertIn("'Send Telegram Message'", error_message)
        self.assertIn("seems to return an array of items", error_message)
        self.assertIn("expects a single item", error_message)
        self.assertIn("Recommendation: Insert a 'Split In Batches' or a 'Code' node", error_message)

    def test_no_error_for_valid_workflow(self):
        """
        Tests that the analyzer does not report errors for a valid workflow.
        """
        mock_workflow = {
            "nodes": [
                {"id": "1", "name": "Start", "type": "n8n-nodes-base.start"},
                {"id": "2", "name": "Get a Single User", "type": "n8n-nodes-base.http-request"},
                {"id": "3", "name": "Send Telegram Message", "type": "n8n-nodes-base.telegram"}
            ],
            "connections": [
                {"source": "1", "target": "2"},
                {"source": "2", "target": "3"}
            ]
        }

        errors = self.analyzer.find_logical_errors(mock_workflow)
        self.assertEqual(len(errors), 0)

    def test_no_error_when_handler_node_is_used(self):
        """
        Tests that no error is reported if an array-handling node (like Split in Batches)
        is placed between the array producer and the single-item consumer.
        """
        mock_workflow = {
            "nodes": [
                {"id": "1", "name": "Start", "type": "n8n-nodes-base.start"},
                {"id": "2", "name": "Get All Users", "type": "n8n-nodes-base.http-request"},
                {"id": "3", "name": "Split In Batches", "type": "n8n-nodes-base.splitInBatches"},
                {"id": "4", "name": "Send Telegram Message", "type": "n8n-nodes-base.telegram"}
            ],
            "connections": [
                {"source": "1", "target": "2"},
                {"source": "2", "target": "3"},
                {"source": "3", "target": "4"}
            ]
        }

        errors = self.analyzer.find_logical_errors(mock_workflow)
        self.assertEqual(len(errors), 0)

if __name__ == '__main__':
    unittest.main()
