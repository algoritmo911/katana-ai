import networkx as nx

class ServiceMap:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_service(self, service_name, health_check_url):
        self.graph.add_node(service_name, url=health_check_url, status="UNKNOWN")

    def add_dependency(self, service_from, service_to):
        self.graph.add_edge(service_from, service_to)

    def get_blast_radius(self, service_name):
        """Returns all services that depend on the given service."""
        if service_name not in self.graph:
            return []
        return list(nx.descendants(self.graph, service_name))

    def get_root_cause(self, service_name):
        """Returns all services that the given service depends on."""
        if service_name not in self.graph:
            return []
        return list(nx.ancestors(self.graph, service_name))

def get_default_service_map():
    """Creates the default service map for the Katana system."""
    service_map = ServiceMap()

    # Define services and their health check URLs
    # Using placeholder URLs for now
    services = {
        "telegram-bot": "http://localhost:8088/health", # Assuming the bot itself has a health endpoint
        "n8n-bridge": "http://localhost:5678/health",
        "neurovault-api": "http://localhost:8042/api/health"
    }

    for name, url in services.items():
        service_map.add_service(name, url)

    # Define dependencies
    service_map.add_dependency("telegram-bot", "n8n-bridge")
    service_map.add_dependency("n8n-bridge", "neurovault-api")

    return service_map
