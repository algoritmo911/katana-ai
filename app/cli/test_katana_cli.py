import unittest
from unittest.mock import patch
from click.testing import CliRunner
from app.cli.katana_cli import cli

class TestCli(unittest.TestCase):
    @patch('requests.get')
    def test_status_command(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "queued"}
        runner = CliRunner()
        result = runner.invoke(cli, ['status', 'test_id'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"status": "queued"', result.output)

    @patch('app.cli.katana_cli.KatanaState')
    def test_cancel_command(self, mock_katana_state):
        runner = CliRunner()
        result = runner.invoke(cli, ['cancel', 'test_id'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Command test_id has been marked for cancellation.", result.output)

    def test_flush_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['flush'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Flushing the command queue is not yet implemented.", result.output)

if __name__ == '__main__':
    unittest.main()
