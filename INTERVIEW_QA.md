# self-service-developer-platform — interview questions and answers

[README](README.md) · [Project architecture](PROJECT_ARCHITECTURE.md)

Answers below use this repository’s files and implementation. They distinguish existing behavior from suggested extensions; source links let you verify each walkthrough.

## 1. What problem does self-service-developer-platform address, and what can you demonstrate?

A developer picks a template, names a service, and asks for an environment. The API runs every check the template needs, lists the files the scaffold would create, and records the request. A second person approves it. Nothing is applied: approval produces the next step, a pull request to the GitOps repository, and Argo CD stays the only writer to the cluster.

I would demonstrate the linked implementation or examples and distinguish that evidence from any planned production features. Start with [`README.md`](README.md).

## 2. How is this repository organized?

- [`src/idp/main.py`](src/idp/main.py): Implementation or supporting configuration.
- [`src/idp/catalog.py`](src/idp/catalog.py): Implementation or supporting configuration.
- [`requirements.txt`](requirements.txt): Implementation or supporting configuration.
- [`tests/test_idp.py`](tests/test_idp.py): Executable checks and regression examples.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml): GitHub Actions job definitions.
- [`README.md`](README.md): Project explanations or operating notes.

[PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) contains the component diagram and the implementation walkthrough.

## 3. Can you walk through `submit` and explain the decision it makes?

The main walkthrough here is `submit(self, request)` in [`src/idp/catalog.py`](src/idp/catalog.py#L57).

```python
    def submit(self, request):
        if request["template"] not in TEMPLATES:
            raise CatalogError(f"template must be one of {', '.join(sorted(TEMPLATES))}")
        if request["environment"] in {"prod", "production"}:
            raise CatalogError("prod is a reviewed GitOps change")
        if request["environment"] not in {"dev", "staging"}:
            raise CatalogError("environment must be dev or staging")
        if not TEAM.fullmatch(request["team"]):
            raise CatalogError("team must be lowercase letters, digits, or dashes")
        duplicate = [
            row
            for row in self.requests
            if row["service"] == request["service"] and row["environment"] == request["environment"] and row["status"] != "rejected"
        ]
        if duplicate:
            raise CatalogError(f"{request['service']} already has {duplicate[0]['id']} in {request['environment']}", status=409)
        checks = self.evaluate(request)
        row = {
            "id": f"req-{len(self.requests) + 1}",
            **request,
```

This is an excerpt; follow the source link for the rest of the branches.

The implementation calls `', '.join`, `CatalogError`, `TEAM.fullmatch`, `all`, `len`, `self.evaluate`, `self.requests.append`, `sorted`. In an interview, trace those calls in execution order using a fixture input.

## 4. What responsibility does `evaluate` have?

`evaluate(self, request)` is defined in [`src/idp/catalog.py`](src/idp/catalog.py#L34).

Its return expressions include:

- `checks`

It uses `NAME.fullmatch`, `bool`, `request.get`, `results.items`. This is the code path I would compare against the caller to explain responsibility boundaries.

## 5. What input validation and failure behavior are implemented?

Explicit failure paths include:

- `CatalogError('request not found', status=404)` in [`src/idp/catalog.py`](src/idp/catalog.py#L90).
- `CatalogError(f"template must be one of {', '.join(sorted(TEMPLATES))}")` in [`src/idp/catalog.py`](src/idp/catalog.py#L59).
- `CatalogError('prod is a reviewed GitOps change')` in [`src/idp/catalog.py`](src/idp/catalog.py#L61).
- `CatalogError('environment must be dev or staging')` in [`src/idp/catalog.py`](src/idp/catalog.py#L63).
- `CatalogError('team must be lowercase letters, digits, or dashes')` in [`src/idp/catalog.py`](src/idp/catalog.py#L65).
- `CatalogError(f"{request['service']} already has {duplicate[0]['id']} in {request['environment']}", status=409)` in [`src/idp/catalog.py`](src/idp/catalog.py#L72).
- `CatalogError(f"{row['id']} is {row['status']}; only a request with every check passed can be approved", status=409)` in [`src/idp/catalog.py`](src/idp/catalog.py#L95).

I would test both the condition that reaches each exception and the caller that translates it. An explicit raise does not mean every malformed input or dependency failure is handled.

## 6. Which test would you use to demonstrate correctness?

[`tests/test_idp.py`](tests/test_idp.py#L34) contains `test_catalog_returns_checks_and_refuses_prod`:

```python
def test_catalog_returns_checks_and_refuses_prod():
    body = submit().json()
    assert body["applied"] is False
    assert [check["name"] for check in body["checks"]] == ["repository", "ci", "helm", "policy", "slo"]
    assert body["status"] == "ready_for_review"
    assert submit(environment="prod").status_code == 422
```

This is a concrete regression example from the repository. Its assertions establish that case; they do not establish behavior for every input or under production load.

## 7. What HTTP interface does the code expose?

- `GET /healthz` → `healthz` in [`src/idp/main.py`](src/idp/main.py#L34).
- `GET /catalog/templates` → `templates` in [`src/idp/main.py`](src/idp/main.py#L39).
- `POST /catalog/requests` → `request_template` in [`src/idp/main.py`](src/idp/main.py#L49).
- `GET /catalog/requests` → `list_requests` in [`src/idp/main.py`](src/idp/main.py#L54).
- `GET /catalog/requests/{request_id}` → `get_request` in [`src/idp/main.py`](src/idp/main.py#L59).
- `POST /catalog/requests/{request_id}/approve` → `approve` in [`src/idp/main.py`](src/idp/main.py#L64).

These are literal decorators. Application/router prefixes, authentication, and middleware must be checked in the corresponding setup code.

## 8. Where does state live, and what happens with multiple workers?

Module-level containers include `TEMPLATES` in [`src/idp/catalog.py`](src/idp/catalog.py).

These containers belong to a Python process. Inspect which are constant fixtures and which are mutated. Mutable process state needs an explicit shared-storage or synchronization strategy before multiple workers can provide consistent behavior.

## 9. How would another engineer reproduce your walkthrough?

Start from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands follow repository manifests; environment setup and command results still need to be checked on the target machine.

## 10. What does automation verify, and what does it not prove?

Inspect [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for triggers, permissions, and job commands. I would name the checks that those definitions run and show the latest run separately. A workflow definition alone does not establish a successful deployment, security review, or production SLO.

## 11. How would you present this project in a Forward Deployed Engineer interview?

Start with the user and operational problem described in [`README.md`](README.md). Explain one constraint that changes the implementation, show the linked code or example, and walk through a success case and a failure case. Agree on a measurable acceptance criterion before expanding the solution, and leave a handoff with data boundaries and rollback ownership. Any proposed production or business metric should be identified as a target until measured.

## 12. What is the input-to-output contract of `submit`?

In [`src/idp/catalog.py`](src/idp/catalog.py#L57), `submit(self, request)` receives the inputs. The function computes these intermediate values:

- `duplicate = [row for row in self.requests if row['service'] == request['service'] and row['environment'] == request['environment'] and (row['status'] != 'rejected')]`
- `checks = self.evaluate(request)`
- `row = {'id': f'req-{len(self.requests) + 1}', **request, 'checks': checks, 'status': 'ready_for_review' if all((check['passed'] for check in checks)) else 'blocked', 'files': [f"{request['service']}/{path}" for path in TEMPLATES[request['template']]['files']], 'approved_by': None, 'applied': False}`

Its result is defined by:

- `row`

## 13. Which decision rules or boundary conditions should an interviewer challenge?

The implementation in [`src/idp/catalog.py`](src/idp/catalog.py#L57) branches on:

- `request['template'] not in TEMPLATES`
- `request['environment'] in {'prod', 'production'}`
- `request['environment'] not in {'dev', 'staging'}`
- `not TEAM.fullmatch(request['team'])`
- `duplicate`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.
