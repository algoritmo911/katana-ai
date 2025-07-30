import unittest
from unittest.mock import patch, Mock
from hydra_observer.probes import run_probes
from hydra_observer.reactor.reaction_core import reaction_core

class TestIntegration(unittest.TestCase):
    @patch('hydra_observer.probes.psutil.cpu_percent')
    @patch('hydra_observer.reactor.reaction_core.ReactionCore.trigger')
    def test_high_cpu_integration(self, mock_trigger, mock_cpu_percent):
        """Tests that a high CPU usage triggers the correct reaction."""
        mock_cpu_percent.return_value = 95

        # We need to run the probes in a way that allows us to exit the loop
        # for testing purposes. We can patch time.sleep to raise an exception.
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            try:
                run_probes(interval=1)
            except KeyboardInterrupt:
                pass

        mock_trigger.assert_called_with("high_cpu", {"cpu_percent": 95})

if __name__ == '__main__':
    unittest.main()
