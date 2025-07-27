class AgentRouter:
    def __init__(self):
        self._agents = {}

    def register_agent(self, agent_name, agent_instance):
        self._agents[agent_name] = agent_instance

    def get_agent(self, agent_name):
        return self._agents.get(agent_name)

    def list_agents(self):
        return list(self._agents.keys())
