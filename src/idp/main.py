from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Internal developer platform")
TEMPLATES = {"python-service", "worker"}


class CatalogRequest(BaseModel):
    template: str
    team: str
    environment: str


@app.post("/catalog/requests")
def request_template(body: CatalogRequest):
    if body.template not in TEMPLATES:
        raise HTTPException(status_code=422, detail="template must be python-service or worker")
    if body.environment in {"prod", "production"}:
        raise HTTPException(status_code=422, detail="prod is a reviewed GitOps change")
    if body.environment not in {"dev", "staging"}:
        raise HTTPException(status_code=422, detail="environment must be dev or staging")
    return {
        "applied": False,
        "template": body.template,
        "team": body.team,
        "checks": ["repository", "ci", "helm", "policy"],
    }
