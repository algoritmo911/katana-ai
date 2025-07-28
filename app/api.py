from flask import Flask, jsonify
import json
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.log import COMMAND_LOG_FILE

app = Flask(__name__)

@app.route('/command/<command_id>', methods=['GET'])
def get_command_status(command_id):
    """Returns the status of a command."""
    if not os.path.exists(COMMAND_LOG_FILE):
        return jsonify({"error": "Command log file not found."}), 404

    with open(COMMAND_LOG_FILE, "r") as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry["command_id"] == command_id:
                return jsonify(log_entry)

    return jsonify({"error": "Command not found."}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)
