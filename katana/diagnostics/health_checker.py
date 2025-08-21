import requests
import threading
import time
from katana.diagnostics.service_map import ServiceMap

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

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                status = "OK"
            else:
                status = f"FAILED (HTTP {response.status_code})"
        except requests.RequestException as e:
            status = f"FAILED ({type(e).__name__})"

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

        for service, data in self.service_map.graph.nodes(data=True):
            status = data.get('status', 'UNKNOWN')
            report_lines.append(f"- {service}: {status}")
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
