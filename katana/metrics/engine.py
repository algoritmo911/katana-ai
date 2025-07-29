from prometheus_client import Counter, Gauge, Histogram

# --- Agent Metrics ---
AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total",
    "Total number of requests to an agent",
    ["agent_id"],
)
AGENT_REQUESTS_SUCCESS = Counter(
    "agent_requests_success",
    "Total number of successful requests to an agent",
    ["agent_id"],
)
AGENT_REQUESTS_FAILURE = Counter(
    "agent_requests_failure",
    "Total number of failed requests to an agent",
    ["agent_id"],
)
AGENT_RESPONSE_TIME = Histogram(
    "agent_response_time_seconds",
    "Response time of an agent",
    ["agent_id"],
)
AGENTS_ONLINE = Gauge(
    "agents_online",
    "Number of online agents",
)


class MetricsEngine:
    def agent_request(self, agent_id: str):
        AGENT_REQUESTS_TOTAL.labels(agent_id=agent_id).inc()

    def agent_success(self, agent_id: str):
        AGENT_REQUESTS_SUCCESS.labels(agent_id=agent_id).inc()

    def agent_failure(self, agent_id: str):
        AGENT_REQUESTS_FAILURE.labels(agent_id=agent_id).inc()

    def agent_response_time(self, agent_id: str, response_time: float):
        AGENT_RESPONSE_TIME.labels(agent_id=agent_id).observe(response_time)

    def set_agents_online(self, count: int):
        AGENTS_ONLINE.set(count)
