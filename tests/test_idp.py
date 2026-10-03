from fastapi.testclient import TestClient

from idp.main import app

client = TestClient(app)


def test_catalog_returns_checks_and_refuses_prod():
    body = client.post("/catalog/requests", json={"template": "python-service", "team": "payments", "environment": "dev"}).json()
    assert body["applied"] is False
    assert body["checks"] == ["repository", "ci", "helm", "policy"]
    assert client.post("/catalog/requests", json={"template": "python-service", "team": "payments", "environment": "prod"}).status_code == 422
