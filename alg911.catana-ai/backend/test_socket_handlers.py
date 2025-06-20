import pytest
import time
from flask import Flask
from flask_socketio import SocketIO
import os
import json

MOCK_COMMANDS_FILE = "mock_katana.commands.json"

# Assuming backend.socket_handlers is importable from the CWD (alg911.catana-ai)
# This might require PYTHONPATH to be set correctly when running pytest, e.g., `PYTHONPATH=. pytest`
from backend.socket_handlers import (
    handle_ping_agent,
    handle_send_command,
    # KATANA_COMMANDS_JSON as ACTUAL_KATANA_COMMANDS_JSON # Not strictly needed if monkeypatching target directly
)
from backend import socket_handlers as socket_handlers_module # For monkeypatching

@pytest.fixture(autouse=True)
def mock_katana_files(monkeypatch):
    if os.path.exists(MOCK_COMMANDS_FILE):
        os.remove(MOCK_COMMANDS_FILE)
    monkeypatch.setattr(socket_handlers_module, 'KATANA_COMMANDS_JSON', MOCK_COMMANDS_FILE)
    yield
    if os.path.exists(MOCK_COMMANDS_FILE):
        os.remove(MOCK_COMMANDS_FILE)

@pytest.fixture
def app_instance(): # Renamed from app to avoid conflict with flask_app import if any
    _app = Flask(__name__)
    _app.config['TESTING'] = True
    return _app

@pytest.fixture
def test_client_factory(app_instance): # Use the renamed app_instance
    def factory():
        socketio = SocketIO(app_instance)
        socketio.on_event('ping_agent', handle_ping_agent)
        socketio.on_event('send_command_to_katana', handle_send_command)
        return socketio.test_client(app_instance)
    return factory

def test_handle_ping_agent(test_client_factory):
    client = test_client_factory()
    client.connect()
    client.emit('ping_agent', {'data': 'test_ping'})
    received = client.get_received()
    ping_response_event = next((r for r in received if r['name'] == 'agent_response' and r['args'][0].get('type') == 'ping_response'), None)
    assert ping_response_event is not None, "No agent_response with type ping_response received"
    response_args = ping_response_event['args'][0]
    assert response_args['status'] == 'success'
    assert 'data' in response_args
    assert 'server_uptime_seconds' in response_args['data']
    assert 'agent_version' in response_args['data']
    assert 'process_metrics' in response_args['data']
    assert os.path.exists(MOCK_COMMANDS_FILE), "Ping should write to commands file"

def test_handle_send_command_valid(test_client_factory):
    client = test_client_factory()
    client.connect()
    test_action = "test_action_from_pytest"
    test_params = {"key": "value"}
    client.emit('send_command_to_katana', {"action": test_action, "parameters": json.dumps(test_params)})
    received = client.get_received()
    command_response_event = next((r for r in received if r['name'] == 'command_response'), None)
    assert command_response_event is not None, "No command_response received"
    response_args = command_response_event['args'][0]
    assert response_args['success'] is True
    assert 'Command test_action_from_pytest sent to Katana' in response_args['message']
    assert 'command_id' in response_args
    assert os.path.exists(MOCK_COMMANDS_FILE)
    with open(MOCK_COMMANDS_FILE, 'r') as f:
        commands_in_file = json.load(f)
    assert len(commands_in_file) == 1
    assert commands_in_file[0]['action'] == test_action
    assert commands_in_file[0]['parameters'] == test_params

def test_handle_send_command_no_action(test_client_factory):
    client = test_client_factory()
    client.connect()
    client.emit('send_command_to_katana', {"parameters": "{}"})
    received = client.get_received()
    command_response_event = next((r for r in received if r['name'] == 'command_response'), None)
    assert command_response_event is not None
    assert command_response_event['args'][0]['success'] is False
    assert command_response_event['args'][0]['message'] == 'Action is required.'
    assert not os.path.exists(MOCK_COMMANDS_FILE) # Should not write if invalid

def test_handle_send_command_invalid_params_json(test_client_factory):
    client = test_client_factory()
    client.connect()
    client.emit('send_command_to_katana', {"action": "test", "parameters": "not_json"})
    received = client.get_received()
    command_response_event = next((r for r in received if r['name'] == 'command_response'), None)
    assert command_response_event is not None
    assert command_response_event['args'][0]['success'] is False
    assert command_response_event['args'][0]['message'] == 'Invalid JSON in parameters.'
    assert not os.path.exists(MOCK_COMMANDS_FILE)
