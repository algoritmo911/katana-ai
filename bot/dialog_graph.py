import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
import uuid

class DialogGraph:
    def __init__(self, user_id):
        self.user_id = user_id
        self.graph = nx.DiGraph()
        self.current_node_id = None
        self._add_initial_node()

    def _add_initial_node(self):
        """Adds the first node to the graph when a user starts a conversation."""
        node_id = str(uuid.uuid4())
        initial_context = {
            "last_recognized_intent": None,
            "last_processed_intent": None,
            "entities": {},
            "history_summary": None,
        }
        self.graph.add_node(
            node_id,
            type="system_start",
            timestamp=datetime.utcnow().isoformat(),
            context=initial_context
        )
        self.current_node_id = node_id

    def add_message_exchange(self, user_text, bot_response, nlp_result, new_context):
        """Adds a user message and a bot response to the graph."""
        parent_node_id = self.current_node_id

        # Create a new node for the user's message
        user_node_id = str(uuid.uuid4())
        self.graph.add_node(
            user_node_id,
            type="user_message",
            text=user_text,
            timestamp=datetime.utcnow().isoformat(),
            nlp_result=nlp_result
        )
        # Connect from the previous node to the user message
        intent_label = nlp_result.get("intents")[0]['name'] if nlp_result.get("intents") else "unknown"
        self.graph.add_edge(parent_node_id, user_node_id, label=f"user: {intent_label}")

        # Create a new node for the bot's response
        bot_node_id = str(uuid.uuid4())
        self.graph.add_node(
            bot_node_id,
            type="bot_response",
            text=bot_response,
            timestamp=datetime.utcnow().isoformat(),
            context=new_context
        )
        # Connect from the user message to the bot response
        self.graph.add_edge(user_node_id, bot_node_id, label="bot_responds")

        self.current_node_id = bot_node_id
        return bot_node_id

    def get_current_context(self):
        """Returns the context from the current node."""
        if self.current_node_id:
            return self.graph.nodes[self.current_node_id].get("context", {})
        return {}

    def to_json(self):
        """Serializes the graph to a JSON-compatible dictionary."""
        return nx.node_link_data(self.graph)

    @classmethod
    def from_json(cls, data, user_id):
        """Deserializes the graph from a JSON-compatible dictionary."""
        instance = cls(user_id)
        instance.graph = nx.node_link_graph(data)
        # Find the latest node to set as current_node_id (a simple approach)
        if instance.graph.nodes:
            latest_node = max(instance.graph.nodes(data=True), key=lambda n: n[1]['timestamp'])
            instance.current_node_id = latest_node[0]
        return instance

    def visualize(self, filename=None):
        """Saves a visualization of the graph to a file."""
        if not filename:
            filename = f"user_{self.user_id}_graph.png"

        plt.figure(figsize=(12, 12))
        pos = nx.spring_layout(self.graph)

        node_labels = {node: f"{data.get('type', 'N/A')}\n({node[:4]})" for node, data in self.graph.nodes(data=True)}
        nx.draw(self.graph, pos, labels=node_labels, with_labels=True, node_size=3000, node_color="skyblue", font_size=8)

        edge_labels = nx.get_edge_attributes(self.graph, 'label')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_color='red')

        plt.title(f"Dialog Graph for User {self.user_id}")
        plt.savefig(filename)
        plt.close()
        return filename
