import unittest
from unittest.mock import patch, MagicMock
import networkx as nx
import requests

from katana.diagnostics.service_map import ServiceMap, get_default_service_map
from katana.diagnostics.health_checker import HealthChecker

class TestServiceMap(unittest.TestCase):

    def test_add_service(self):
        sm = ServiceMap()
        sm.add_service("test-service", "http://test.com/health")
        self.assertIn("test-service", sm.graph)
        self.assertEqual(sm.graph.nodes["test-service"]["url"], "http://test.com/health")
        self.assertEqual(sm.graph.nodes["test-service"]["status"], "UNKNOWN")

    def test_add_dependency(self):
        sm = ServiceMap()
        sm.add_service("service-a", "url-a")
        sm.add_service("service-b", "url-b")
        sm.add_dependency("service-a", "service-b")
        self.assertIn("service-b", sm.graph.successors("service-a"))

    def test_get_blast_radius(self):
        sm = get_default_service_map()
        # telegram-bot -> n8n-bridge -> neurovault-api
        self.assertEqual(set(sm.get_blast_radius("telegram-bot")), {"n8n-bridge", "neurovault-api"})
        self.assertEqual(set(sm.get_blast_radius("n8n-bridge")), {"neurovault-api"})
        self.assertEqual(sm.get_blast_radius("neurovault-api"), [])

    def test_get_root_cause(self):
        sm = get_default_service_map()
        # telegram-bot -> n8n-bridge -> neurovault-api
        self.assertEqual(sm.get_root_cause("telegram-bot"), [])
        self.assertEqual(set(sm.get_root_cause("n8n-bridge")), {"telegram-bot"})
        self.assertEqual(set(sm.get_root_cause("neurovault-api")), {"telegram-bot", "n8n-bridge"})


class TestHealthChecker(unittest.TestCase):

    def setUp(self):
        self.service_map = get_default_service_map()
        self.health_checker = HealthChecker(self.service_map)

    @patch('requests.get')
    def test_check_service_health_ok(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        status = self.health_checker.check_service_health("n8n-bridge")
        self.assertEqual(status, "OK")
        self.assertEqual(self.service_map.graph.nodes["n8n-bridge"]["status"], "OK")

    @patch('requests.get')
    def test_check_service_health_failed_http(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        status = self.health_checker.check_service_health("n8n-bridge")
        self.assertEqual(status, "FAILED (HTTP 503)")
        self.assertEqual(self.service_map.graph.nodes["n8n-bridge"]["status"], "FAILED (HTTP 503)")

    @patch('requests.get')
    def test_check_service_health_failed_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError

        status = self.health_checker.check_service_health("n8n-bridge")
        self.assertEqual(status, "FAILED (ConnectionError)")
        self.assertEqual(self.service_map.graph.nodes["n8n-bridge"]["status"], "FAILED (ConnectionError)")

    def test_get_system_status_report_all_ok(self):
        # Set all services to OK
        for service in self.service_map.graph.nodes:
            self.service_map.graph.nodes[service]['status'] = "OK"

        report = self.health_checker.get_system_status_report()
        self.assertIn("All systems are operational.", report)

    def test_get_system_status_report_one_failure(self):
        # Set one service to FAILED
        self.service_map.graph.nodes['telegram-bot']['status'] = "OK"
        self.service_map.graph.nodes['n8n-bridge']['status'] = "FAILED (HTTP 500)"
        self.service_map.graph.nodes['neurovault-api']['status'] = "OK"

        report = self.health_checker.get_system_status_report()
        self.assertIn("Failure in 'n8n-bridge'", report)
        self.assertIn("Impact Zone (affected services): neurovault-api", report)
        self.assertIn("Potential Root Cause: This service appears to be the origin of the failure.", report)

    def test_get_system_status_report_root_cause_failure(self):
        # Set a root service to FAILED, which causes a cascade
        self.service_map.graph.nodes['telegram-bot']['status'] = "OK"
        self.service_map.graph.nodes['n8n-bridge']['status'] = "FAILED (Timeout)"
        self.service_map.graph.nodes['neurovault-api']['status'] = "FAILED (ConnectionError)" # This one is also failing

        report = self.health_checker.get_system_status_report()
        self.assertIn("Failure in 'neurovault-api'", report)
        # Check that the report correctly identifies 'n8n-bridge' as a potential root cause for 'neurovault-api' failure
        self.assertIn("Potential Root Cause(s): n8n-bridge", report)


if __name__ == '__main__':
    unittest.main()
