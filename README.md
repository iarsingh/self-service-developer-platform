# Self-service internal developer platform

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
