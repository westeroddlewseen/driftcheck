# driftcheck

Detect configuration drift between deployed services and their expected state in Git.

---

## Installation

```bash
pip install driftcheck
```

Or install from source:

```bash
git clone https://github.com/yourorg/driftcheck.git && cd driftcheck && pip install .
```

---

## Usage

Point `driftcheck` at your live service endpoint and the corresponding config in your repository:

```bash
driftcheck --service my-api --git-path ./config/my-api.yaml --env production
```

Example output:

```
[DRIFT DETECTED] my-api (production)
  ✗ replicas: expected 3, found 1
  ✗ image.tag: expected "v2.4.1", found "v2.3.0"
  ✓ port: 8080

2 drift(s) found across 1 service(s).
```

Run against multiple services using a config file:

```bash
driftcheck --config driftcheck.yml --env staging
```

Exit with a non-zero status code when drift is detected (useful in CI pipelines):

```bash
driftcheck --config driftcheck.yml --env production --fail-on-drift
```

Check the [docs](./docs) for full configuration options and CI integration examples.

---

## Configuration

`driftcheck.yml` example:

```yaml
services:
  - name: my-api
    git_path: ./config/my-api.yaml
    endpoint: https://api.internal/my-api/config
  - name: worker
    git_path: ./config/worker.yaml
    endpoint: https://api.internal/worker/config
```

---

## License

This project is licensed under the [MIT License](./LICENSE).
