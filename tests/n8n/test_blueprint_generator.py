import pytest
from src.n8n.blueprint_generator import N8nBlueprintGenerator

class TestN8nBlueprintGenerator:

    @pytest.fixture
    def generator(self):
        """Provides an instance of the N8nBlueprintGenerator."""
        return N8nBlueprintGenerator()

    def test_generate_standard_lead_funnel_structure(self, generator):
        """
        Tests the basic structure of the generated 'StandardLeadFunnel' workflow.
        """
        workflow = generator.generate_workflow('StandardLeadFunnel')

        assert isinstance(workflow, dict)
        assert 'name' in workflow
        assert workflow['name'] == 'Standard Lead Funnel'
        assert 'nodes' in workflow
        assert 'connections' in workflow
        assert 'active' in workflow
        assert workflow['active'] is False

    def test_generate_standard_lead_funnel_nodes(self, generator):
        """
        Tests the nodes in the generated 'StandardLeadFunnel' workflow.
        """
        workflow = generator.generate_workflow('StandardLeadFunnel')
        nodes = workflow['nodes']

        assert len(nodes) == 6

        # Check for node types
        expected_types = [
            'n8n-nodes-base.webhook',
            'n8n-nodes-base.set',
            'n8n-nodes-base.if',
            'n8n-nodes-base.googleSheets',
            'n8n-nodes-base.telegram',
            'n8n-nodes-base.respondToWebhook'
        ]
        actual_types = [node['type'] for node in nodes]
        assert sorted(actual_types) == sorted(expected_types)

        # Check for unique node IDs
        node_ids = [node['id'] for node in nodes]
        assert len(node_ids) == len(set(node_ids)), "Node IDs are not unique"

    def test_generate_standard_lead_funnel_connections(self, generator):
        """
        Tests the connections in the generated 'StandardLeadFunnel' workflow.
        """
        workflow = generator.generate_workflow('StandardLeadFunnel')
        connections = workflow['connections']

        # Helper to find node by name
        nodes_by_name = {node['name']: node for node in workflow['nodes']}

        webhook_node = nodes_by_name['Webhook']
        set_node = nodes_by_name['Set Lead Source']
        if_node = nodes_by_name['Is Paid Lead?']
        gsheets_node = nodes_by_name['Save to Google Sheet']
        telegram_node = nodes_by_name['Notify via Telegram']
        respond_node = nodes_by_name['Respond to Webhook']

        # Webhook -> Set
        assert connections[webhook_node['name']]['main'][0][0]['node'] == set_node['name']

        # Set -> IF
        assert connections[set_node['name']]['main'][0][0]['node'] == if_node['name']

        # IF -> Google Sheets (true output, index 0)
        if_true_output = connections[if_node['name']]['main'][0][0]
        assert if_true_output['node'] == gsheets_node['name']

        # IF -> Telegram (false output, index 1)
        if_false_output = connections[if_node['name']]['main'][1][0]
        assert if_false_output['node'] == telegram_node['name']

        # Google Sheets -> Respond
        assert connections[gsheets_node['name']]['main'][0][0]['node'] == respond_node['name']

        # Telegram -> Respond
        assert connections[telegram_node['name']]['main'][0][0]['node'] == respond_node['name']

    def test_unknown_template_raises_error(self, generator):
        """
        Tests that requesting a non-existent template raises a ValueError.
        """
        with pytest.raises(ValueError, match="Template 'NonExistentTemplate' not found."):
            generator.generate_workflow('NonExistentTemplate')
