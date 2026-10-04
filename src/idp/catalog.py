import re

NAME = re.compile(r"^[a-z][a-z0-9-]{1,30}[a-z0-9]$")
TEAM = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
TEMPLATES = {
    "python-service": {
        "description": "HTTP service on FastAPI with a Service and an Ingress",
        "checks": ["repository", "ci", "helm", "policy", "slo"],
        "files": ["app/main.py", "Dockerfile", ".github/workflows/ci.yml", "helm/values.yaml", "slo.yaml", "CODEOWNERS"],
        "max_replicas": {"dev": 2, "staging": 4},
    },
    "worker": {
        "description": "Queue consumer with no Service and no Ingress",
        "checks": ["repository", "ci", "helm", "policy"],
        "files": ["worker/main.py", "Dockerfile", ".github/workflows/ci.yml", "helm/values.yaml", "CODEOWNERS"],
        "max_replicas": {"dev": 1, "staging": 3},
    },
}


class CatalogError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


class Catalog:
    def __init__(self):
        self.requests = []

    def clear(self):
        self.requests.clear()

    def evaluate(self, request):
        template = TEMPLATES[request["template"]]
        cap = template["max_replicas"][request["environment"]]
        results = {
            "repository": bool(NAME.fullmatch(request["service"])),
            "ci": True,
            "helm": 1 <= request["replicas"] <= cap,
            "policy": bool(request["owner"]) and bool(request["cost_center"]),
        }
        if "slo" in template["checks"]:
            results["slo"] = request.get("availability_target") is not None and 95.0 <= request["availability_target"] <= 99.95
        failures = {
            "repository": "service name must be 3 to 32 lowercase letters, digits, or dashes",
            "helm": f"replicas must be from 1 to {cap} for {request['template']} in {request['environment']}",
            "policy": "owner and cost_center are required",
            "slo": "a python-service needs an availability target from 95 to 99.95",
        }
        checks = [
            {"name": name, "passed": passed, **({} if passed else {"reason": failures[name]})}
            for name, passed in results.items()
        ]
        return checks

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
            "checks": checks,
            "status": "ready_for_review" if all(check["passed"] for check in checks) else "blocked",
            "files": [f"{request['service']}/{path}" for path in TEMPLATES[request["template"]]["files"]],
            "approved_by": None,
            "applied": False,
        }
        self.requests.append(row)
        return row

    def get(self, request_id):
        for row in self.requests:
            if row["id"] == request_id:
                return row
        raise CatalogError("request not found", status=404)

    def approve(self, request_id, reviewer):
        row = self.get(request_id)
        if row["status"] != "ready_for_review":
            raise CatalogError(f"{row['id']} is {row['status']}; only a request with every check passed can be approved", status=409)
        if reviewer == row["requested_by"]:
            raise CatalogError("the requester cannot approve their own request", status=403)
        row["status"] = "approved"
        row["approved_by"] = reviewer
        row["next_step"] = "A pull request with these files goes to the GitOps repository. Argo CD applies it after merge."
        return row
