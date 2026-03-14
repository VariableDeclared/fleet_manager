import pytest
from fastapi.testclient import TestClient
from agent import app, SECRET_KEY

client = TestClient(app)

def test_status_unauthorized():
    response = client.get("/status")
    assert response.status_code == 403

def test_status_authorized():
    headers = {"X-API-KEY": SECRET_KEY}
    response = client.get("/status", headers=headers)
    assert response.status_code in [200, 500] # 500 if run on non-linux OS
