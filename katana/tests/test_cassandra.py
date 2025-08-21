import unittest
from katana.diagnostics.service_map import get_default_service_map
from katana.cassandra.precog_engine import PrecogEngine, HIGH_LATENCY_THRESHOLD_MS, HIGH_ERROR_RATE_THRESHOLD

class TestDigitalTwin(unittest.TestCase):

    def test_service_map_stores_metrics(self):
        sm = get_default_service_map()
        self.assertIn("metrics", sm.graph.nodes["n8n-bridge"])
        self.assertIn("cpu", sm.graph.nodes["n8n-bridge"]["metrics"])

    def test_update_metrics(self):
        sm = get_default_service_map()
        new_metrics = {"cpu": 55.5, "latency": 123.4}
        sm.update_service_metrics("n8n-bridge", new_metrics)
        self.assertEqual(sm.graph.nodes["n8n-bridge"]["metrics"]["cpu"], 55.5)
        self.assertEqual(sm.graph.nodes["n8n-bridge"]["metrics"]["latency"], 123.4)


class TestPrecogEngine(unittest.TestCase):

    def setUp(self):
        self.digital_twin = get_default_service_map()
        self.precog = PrecogEngine(self.digital_twin)

    def test_pft_generation_no_predictions(self):
        """Test that no predictions are made when metrics are normal."""
        pft = self.precog.generate_pft()
        self.assertEqual(len(pft["root_node"]["children"]), 0)

    def test_pft_high_latency_prediction(self):
        """Test that a high latency metric triggers a prediction."""
        self.digital_twin.update_service_metrics("n8n-bridge", {"latency": HIGH_LATENCY_THRESHOLD_MS + 1})
        pft = self.precog.generate_pft()

        children = pft["root_node"]["children"]
        self.assertEqual(len(children), 1)

        prediction = children[0]
        self.assertEqual(prediction["prediction_source"], "RuleBased_HighLatency")
        self.assertIn("n8n-bridge", prediction["state_change"])
        self.assertEqual(prediction["state_change"]["n8n-bridge"]["status"], "PREDICTED_FAILURE_LATENCY")

    def test_pft_high_error_rate_prediction(self):
        """Test that a high error rate metric triggers a prediction."""
        self.digital_twin.update_service_metrics("neurovault-api", {"error_rate": HIGH_ERROR_RATE_THRESHOLD + 0.1})
        pft = self.precog.generate_pft()

        children = pft["root_node"]["children"]
        self.assertEqual(len(children), 1)

        prediction = children[0]
        self.assertEqual(prediction["prediction_source"], "RuleBased_HighErrorRate")
        self.assertIn("neurovault-api", prediction["state_change"])
        self.assertEqual(prediction["state_change"]["neurovault-api"]["status"], "PREDICTED_FAILURE_ERRORS")

    def test_pft_cascade_failure_prediction(self):
        """Test that a predicted failure causes a cascade prediction."""
        # n8n-bridge -> neurovault-api
        # High latency on n8n-bridge should predict its failure, and then a cascade to neurovault-api
        self.digital_twin.update_service_metrics("n8n-bridge", {"latency": HIGH_LATENCY_THRESHOLD_MS + 1})
        pft = self.precog.generate_pft()

        children = pft["root_node"]["children"]
        self.assertEqual(len(children), 1)

        n8n_prediction = children[0]
        self.assertEqual(len(n8n_prediction["children"]), 1)

        cascade_prediction = n8n_prediction["children"][0]
        self.assertEqual(cascade_prediction["prediction_source"], "RuleBased_Cascade_from_n8n-bridge")
        self.assertIn("neurovault-api", cascade_prediction["state_change"])
        self.assertEqual(cascade_prediction["state_change"]["neurovault-api"]["status"], "PREDICTED_CASCADE_FAILURE")

    def test_pft_no_cascade_to_unrelated_service(self):
        """Test that a cascade does not affect unrelated services."""
        # telegram-bot -> n8n-bridge -> neurovault-api
        # A failure in neurovault-api should not cascade to telegram-bot
        self.digital_twin.update_service_metrics("neurovault-api", {"latency": HIGH_LATENCY_THRESHOLD_MS + 1})
        pft = self.precog.generate_pft()

        children = pft["root_node"]["children"]
        self.assertEqual(len(children), 1) # Only one prediction for neurovault-api

        neurovault_prediction = children[0]
        self.assertEqual(len(neurovault_prediction["children"]), 0) # No cascade children


if __name__ == '__main__':
    unittest.main()
