import requests
import threading
import time
from katana.diagnostics.service_map import ServiceMap
from katana.cassandra.observers import hydra_observer, memory_weaver_observer

class HealthChecker:
    def __init__(self, service_map: ServiceMap):
        self.service_map = service_map

    def check_service_health(self, service_name: str) -> str:
        """
        Checks the health of a single service and updates its status in the map.
        Returns the status string ('OK', 'FAILED', or 'UNKNOWN').
        """
        if service_name not in self.service_map.graph:
            return "UNKNOWN"

        url = self.service_map.graph.nodes[service_name].get('url')
        if not url:
            self.service_map.graph.nodes[service_name]['status'] = "UNKNOWN"
            return "UNKNOWN"

        start_time = time.time()
        try:
            response = requests.get(url, timeout=5)
            latency = round((time.time() - start_time) * 1000) # Latency in ms

            if response.status_code == 200:
                status = "OK"
                # On success, gather metrics from all sources
                all_metrics = {
                    "latency": latency,
                    "error_rate": 0.0, # Success means error rate is 0 for this check
                }
                all_metrics.update(hydra_observer.get_infra_metrics(service_name))
                all_metrics.update(memory_weaver_observer.get_knowledge_graph_metrics(service_name))
                self.service_map.update_service_metrics(service_name, all_metrics)
            else:
                status = f"FAILED (HTTP {response.status_code})"
                # On failure, we can still record latency, but other metrics might be stale
                self.service_map.update_service_metrics(service_name, {"latency": latency, "error_rate": 1.0})

        except requests.RequestException as e:
            latency = round((time.time() - start_time) * 1000)
            status = f"FAILED ({type(e).__name__})"
            # On exception, we can still record latency
            self.service_map.update_service_metrics(service_name, {"latency": latency, "error_rate": 1.0})

        self.service_map.graph.nodes[service_name]['status'] = status
        return status

    def run_all_checks(self):
        """Runs health checks for all services in the map."""
        for service_name in self.service_map.graph.nodes:
            self.check_service_health(service_name)

    def get_system_status_report(self) -> str:
        """Generates a human-readable report of the system's health."""
        report_lines = ["System Health Status:"]
        failed_services = []

        for service, data in sorted(self.service_map.graph.nodes(data=True)):
            status = data.get('status', 'UNKNOWN')
            metrics_str = ", ".join(f"{k}={v}" for k, v in data.get('metrics', {}).items())
            report_lines.append(f"- {service}: {status} [{metrics_str}]")
            if "FAILED" in status:
                failed_services.append(service)

        if failed_services:
            report_lines.append("\nAnalysis of Failures:")
            for service in failed_services:
                blast_radius = self.service_map.get_blast_radius(service)
                root_causes = self.service_map.get_root_cause(service)

                report_lines.append(f"\n- Failure in '{service}':")
                if blast_radius:
                    report_lines.append(f"  - Impact Zone (affected services): {', '.join(blast_radius)}")
                else:
                    report_lines.append("  - Impact Zone: This service has no downstream dependencies.")

                # Check status of root causes to find the likely origin
                potential_causes = []
                for cause in root_causes:
                    if "FAILED" in self.service_map.graph.nodes[cause].get('status', 'UNKNOWN'):
                        potential_causes.append(cause)

                if potential_causes:
                     report_lines.append(f"  - Potential Root Cause(s): {', '.join(potential_causes)}")
                else:
                     report_lines.append("  - Potential Root Cause: This service appears to be the origin of the failure.")

        else:
            report_lines.append("\nAll systems are operational.")

        return "\n".join(report_lines)

    def start_periodic_checks(self, interval_seconds: int = 60):
        """Starts running health checks in a background thread."""
        def checker_loop():
            while True:
                print("Running periodic health checks...")
                self.run_all_checks()
                time.sleep(interval_seconds)

        # Run the loop in a daemon thread so it doesn't block program exit
        thread = threading.Thread(target=checker_loop, daemon=True)
        thread.start()
        print(f"Health checker started in background thread. Interval: {interval_seconds}s")
