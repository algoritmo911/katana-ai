from flask import Flask, request
import requests

app = Flask(__name__)

@app.route("/command", methods=["POST"])
def command():
    command = request.json["command"]
    # Get an access token from the OAuth server
    response = requests.post("http://localhost:8000/oauth/token")
    if response.status_code == 200:
        access_token = response.json()["access_token"]
        # In a real application, we would use the access token to make a request to the Google API
        return {"response": f"Command '{command}' executed successfully with token {access_token}"}
    else:
        return {"error": "Error obtaining access token"}

if __name__ == "__main__":
    app.run(port=5000)
