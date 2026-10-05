from idp.ops import router as ops_router
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from idp.catalog import TEMPLATES, Catalog, CatalogError

app = FastAPI(title="Internal developer platform")
app.include_router(ops_router, prefix="/v1")
CATALOG = Catalog()


class CatalogRequest(BaseModel):
    template: str
    team: str
    environment: str
    service: str = "payments-api"
    replicas: int = 1
    owner: str = ""
    cost_center: str = ""
    availability_target: float | None = None
    requested_by: str = "developer"


class Approval(BaseModel):
    reviewer: str = Field(min_length=1)


def guarded(action):
    try:
        return action()
    except CatalogError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/catalog/templates")
def templates():
    return {
        "templates": [
            {"name": name, "description": spec["description"], "checks": spec["checks"], "max_replicas": spec["max_replicas"]}
            for name, spec in TEMPLATES.items()
        ]
    }


@app.post("/catalog/requests", status_code=201)
def request_template(body: CatalogRequest):
    return guarded(lambda: CATALOG.submit(body.model_dump()))


@app.get("/catalog/requests")
def list_requests(team: str | None = None):
    return {"requests": [row for row in CATALOG.requests if team is None or row["team"] == team]}


@app.get("/catalog/requests/{request_id}")
def get_request(request_id: str):
    return guarded(lambda: CATALOG.get(request_id))


@app.post("/catalog/requests/{request_id}/approve")
def approve(request_id: str, body: Approval):
    return guarded(lambda: CATALOG.approve(request_id, body.reviewer))
