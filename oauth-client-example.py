import requests

response = requests.post("http://localhost:8000/oauth/token")

if response.status_code == 200:
    print("Successfully obtained token:")
    print(response.json())
else:
    print("Error obtaining token:")
    print(response.text)
