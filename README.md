# Self-service internal developer platform

<!-- project-guide:start -->
## Project guide

[Project architecture](PROJECT_ARCHITECTURE.md) · [Interview questions and answers](INTERVIEW_QA.md)

Use the architecture document for the component diagram, implementation boundaries, and verification entry points. The interview guide includes source-backed answers and project walkthroughs.

### Implementation map

| Component | Responsibility |
| --- | --- |
| [`src/idp/main.py`](src/idp/main.py) | HTTP handlers: `GET /healthz`, `GET /catalog/templates`, `POST /catalog/requests`, `GET /catalog/requests`, `GET /catalog/requests/{request_id}` |
| [`src/idp/catalog.py`](src/idp/catalog.py) | Functions: `__init__`, `__init__`, `clear`, `evaluate`, `submit`, `get`, `approve` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`tests/test_idp.py`](tests/test_idp.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |

### Local setup and verification

From the repository root (the commands follow the checked-in manifests):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

To serve the FastAPI application locally, install the server separately if it is not already available:

```bash
python -m pip install uvicorn
PYTHONPATH=src python -m uvicorn idp.main:app --reload
```

<!-- project-guide:end -->

Level: Advanced

Skills: golden-path templates, policy checks, GitOps, CI/CD, four-eyes approval, APIs

A developer picks a template, names a service, and asks for an environment. The API runs every check the template needs, lists the files the scaffold would create, and records the request. A second person approves it. Nothing is applied: approval produces the next step, a pull request to the GitOps repository, and Argo CD stays the only writer to the cluster.

| Template | Checks | Replica cap (dev / staging) |
| --- | --- | --- |
| `python-service` | repository, ci, helm, policy, slo | 2 / 4 |
| `worker` | repository, ci, helm, policy | 1 / 3 |

```bash
pip install -r requirements.txt
pytest -q
PYTHONPATH=src uvicorn idp.main:app --reload
```

```bash
curl -s -X POST localhost:8000/catalog/requests -H 'content-type: application/json' -d '{
  "template": "python-service", "team": "payments", "environment": "dev",
  "service": "payments-api", "replicas": 2, "owner": "ada", "cost_center": "cc-104",
  "availability_target": 99.5, "requested_by": "ada"
}'
```

Each check comes back with `passed`, and a failed check carries the reason. One failed check makes the request `blocked`; all passed makes it `ready_for_review`.

## What it refuses

- `prod`. Production is a reviewed GitOps change.
- A second request for the same service and environment while one is open (409).
- Approving a blocked request (409).
- The requester approving their own request (403).
- A `python-service` without an availability target from 95 to 99.95.
