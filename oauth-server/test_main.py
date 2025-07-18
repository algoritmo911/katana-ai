from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)


def test_get_token():
    response = client.post("/oauth/token")
    assert response.status_code == 200
    assert response.json() == {"access_token": "dummy_token", "token_type": "bearer"}
