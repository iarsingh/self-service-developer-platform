import pytest
from fastapi.testclient import TestClient

from idp.main import CATALOG, app

client = TestClient(app)

GOOD = {
    "template": "python-service",
    "team": "payments",
    "environment": "dev",
    "service": "payments-api",
    "replicas": 2,
    "owner": "ada",
    "cost_center": "cc-104",
    "availability_target": 99.5,
    "requested_by": "ada",
}


@pytest.fixture(autouse=True)
def empty():
    CATALOG.clear()


def submit(**overrides):
    return client.post("/catalog/requests", json={**GOOD, **overrides})


def failed(body):
    return [check["name"] for check in body["checks"] if not check["passed"]]


def test_catalog_returns_checks_and_refuses_prod():
    body = submit().json()
    assert body["applied"] is False
    assert [check["name"] for check in body["checks"]] == ["repository", "ci", "helm", "policy", "slo"]
    assert body["status"] == "ready_for_review"
    assert submit(environment="prod").status_code == 422


def test_worker_has_no_slo_check():
    body = submit(template="worker", service="payments-worker", replicas=1, availability_target=None).json()
    assert [check["name"] for check in body["checks"]] == ["repository", "ci", "helm", "policy"]
    assert body["status"] == "ready_for_review"


def test_replica_cap_depends_on_template_and_environment():
    body = submit(replicas=3).json()
    assert failed(body) == ["helm"]
    assert body["status"] == "blocked"
    assert submit(environment="staging", replicas=3).json()["status"] == "ready_for_review"


def test_missing_owner_and_slo_block_the_request():
    body = submit(owner="", availability_target=None).json()
    assert failed(body) == ["policy", "slo"]
    assert "owner and cost_center" in body["checks"][3]["reason"]


def test_scaffold_files_are_listed_under_the_service():
    files = submit().json()["files"]
    assert "payments-api/slo.yaml" in files
    assert "payments-api/CODEOWNERS" in files


def test_duplicate_service_in_the_same_environment_is_409():
    submit()
    assert submit().status_code == 409
    assert submit(environment="staging").status_code == 201


def test_requester_cannot_approve_their_own_request():
    created = submit().json()
    own = client.post(f"/catalog/requests/{created['id']}/approve", json={"reviewer": "ada"})
    assert own.status_code == 403
    approved = client.post(f"/catalog/requests/{created['id']}/approve", json={"reviewer": "grace"}).json()
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "grace"
    assert approved["applied"] is False


def test_blocked_request_cannot_be_approved():
    created = submit(owner="").json()
    response = client.post(f"/catalog/requests/{created['id']}/approve", json={"reviewer": "grace"})
    assert response.status_code == 409


def test_templates_and_listing():
    names = [row["name"] for row in client.get("/catalog/templates").json()["templates"]]
    assert names == ["python-service", "worker"]
    submit()
    assert len(client.get("/catalog/requests", params={"team": "payments"}).json()["requests"]) == 1
    assert client.get("/catalog/requests/req-99").status_code == 404
