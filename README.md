# Self-service internal developer platform

Level: Advanced

Skills: Terraform-shaped checks, Kubernetes, GitOps, CI/CD, APIs

A developer picks `python-service` or `worker`. The API returns the four checks that have to exist before anything is applied: repository, CI, Helm, and policy. Production is refused. `applied` is false.

This is the catalog, not the cluster. GitOps remains the writer.

```bash
pip install -r requirements.txt
pytest -q
```

