import unittest
import os
from pathlib import Path
import yaml

# Add the project root to the path to allow direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from katana.wanderer.guardian import GuardianProxy
from katana.wanderer.parser import extract_main_content

class TestWandererComponents(unittest.TestCase):

    def setUp(self):
        """Set up a controlled test environment."""
        # Create a dummy protocol file to ensure tests are repeatable
        self.test_protocol_path = "test_safety_protocol.yml"
        self.test_config = {
            'network_rules': {
                'always_obey_robots_txt': True,
                'max_requests_per_host_per_minute': 10,
                'user_agent': "TestWanderer/1.0"
            },
            'content_rules': {
                'never_execute_fetched_code_outside_sandbox': True,
                'forbidden_file_types': ['.exe', '.sh']
            },
            'ethical_rules': {
                'no_denial_of_service': True
            }
        }
        with open(self.test_protocol_path, 'w') as f:
            yaml.dump(self.test_config, f)

    def tearDown(self):
        """Clean up the environment after tests."""
        if os.path.exists(self.test_protocol_path):
            os.remove(self.test_protocol_path)

    def test_guardian_loads_protocol_correctly(self):
        """
        Verify that the GuardianProxy class correctly loads and parses
        the specified safety protocol YAML file.
        """
        # Initialize GuardianProxy with our test protocol file
        guardian = GuardianProxy(protocol_path=self.test_protocol_path)

        # Assert that the rules were loaded
        self.assertIsNotNone(guardian.rules)
        self.assertIn('network_rules', guardian.rules)

        # Assert that a specific value is correctly read
        expected_user_agent = self.test_config['network_rules']['user_agent']
        self.assertEqual(guardian.network_rules['user_agent'], expected_user_agent)
        print(f"\nGuardian User-Agent check PASSED.")

    def test_parser_extracts_main_content(self):
        """
        Verify that the extract_main_content function correctly identifies
        and extracts the main article from a sample HTML document.
        """
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page Title</title>
        </head>
        <body>
            <header>
                <h1>Website Logo</h1>
                <nav>
                    <a href="/home">Home</a>
                    <a href="/about">About</a>
                </nav>
            </header>
            <main>
                <article>
                    <h2>Main Article Title</h2>
                    <p>This is the first paragraph of the main content.</p>
                    <p>This is the second paragraph, which should be extracted.</p>
                </article>
            </main>
            <aside>
                <p>This is a sidebar and should be ignored.</p>
            </aside>
            <footer>
                <p>Copyright 2024. This footer should be ignored.</p>
            </footer>
        </body>
        </html>
        """

        extracted_data = extract_main_content(sample_html)

        # Check title
        self.assertEqual(extracted_data['title'], "Test Page Title")

        # Check that main content is present
        self.assertIn("Main Article Title", extracted_data['content_text'])
        self.assertIn("first paragraph of the main content", extracted_data['content_text'])

        # Check that boilerplate/ads are NOT present
        self.assertNotIn("Website Logo", extracted_data['content_text'])
        self.assertNotIn("This is a sidebar", extracted_data['content_text'])
        self.assertNotIn("Copyright 2024", extracted_data['content_text'])

        print(f"Parser main content extraction check PASSED.")

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
