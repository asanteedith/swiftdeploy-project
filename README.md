# SwiftDeploy — Declarative Infrastructure CLI

> **A CLI tool that generates your entire infrastructure from a single file, enforces deployment policies automatically, and gives you full visibility into every decision it makes.**

---

## Why SwiftDeploy?

Most deployment tools ask you to manually write Dockerfiles, Nginx configs, and Compose files — then hope everything is consistent. SwiftDeploy flips that model.

**You edit one file. SwiftDeploy handles everything else.**

-  **Policy-gated** — deploys only when OPA approves. No human needed to check if the server has enough disk or if the canary is healthy
-  **Observable** — real-time metrics, live dashboard, and a full audit trail of every decision
-  **Reproducible** — delete all generated files and run `init` again. You get the exact same stack
-  **Fast** — one command from zero to running stack with health checks
-  **Smart** — the tool thinks before it acts. It checks policies, scrapes metrics, and blocks unsafe operations automatically

---

## Live Demo
- GitHub: https://github.com/asanteedith/swiftdeploy-project
- Blog: https://dev.to/edithasante/building-a-policy-gated-deployment-system-with-observability-swiftdeploy-stage-4b-4od2

---

## Prerequisites
- Python 3.10+
- Docker Desktop
- pip packages: `pyyaml requests psutil`

---

## Quick Start

```bash
git clone https://github.com/asanteedith/swiftdeploy-project.git
cd swiftdeploy-project
pip install pyyaml requests psutil
docker compose up -d opa
python swiftdeploy.py deploy
```

That is it. One command deploys Nginx, your app, and the OPA policy engine — after verifying your infrastructure is healthy enough to handle it.

---

## How It Works

```
manifest.yaml  ← the only file you edit
     |
swiftdeploy CLI
     |
docker-compose.yml + nginx.conf  ← generated automatically
     |
Docker Network
     |
[Nginx] → [App (/metrics)] → [OPA Policy Engine]
     |
CLI reads metrics → sends to OPA → deploy or block
```

---

## Subcommands

### `init`
Parses `manifest.yaml` and generates `nginx.conf` and `docker-compose.yml` from templates.

**Value:** Delete your configs anytime. One command regenerates everything perfectly.

```bash
python swiftdeploy.py init
```

---

### `validate`
Runs 5 pre-flight checks before anything touches your server.

**Value:** Catches problems before they cause downtime — wrong image, port conflict, bad config.

```bash
python swiftdeploy.py validate
```

Checks:
1. `manifest.yaml` exists and is valid YAML
2. All required fields are present and non-empty
3. Docker image exists locally
4. Nginx port is not already in use
5. `nginx.conf` is syntactically valid

---

### `deploy`
Runs `init`, queries OPA for infrastructure policy approval, brings up the full stack, and waits for health checks to pass.

**Value:** You never deploy to an unhealthy server again. OPA checks disk space and CPU load before a single container starts.

```bash
python swiftdeploy.py deploy
```

---

### `promote`
Switches deployment mode with a rolling restart. Canary promotion requires OPA canary safety approval.

**Value:** You can never accidentally promote a broken canary. SwiftDeploy scrapes live metrics and blocks promotion if error rate or latency is too high.

```bash
python swiftdeploy.py promote canary
python swiftdeploy.py promote stable
```

---

### `teardown`
Removes all containers, networks, and volumes cleanly.

```bash
python swiftdeploy.py teardown
python swiftdeploy.py teardown --clean  # also deletes generated configs
```

---

### `status`
Live terminal dashboard that scrapes `/metrics` every 5 seconds and shows real-time system state and policy compliance.

**Value:** You see exactly what is happening — mode, error rate, latency, and whether OPA policies are currently passing or failing.

```bash
python swiftdeploy.py status
```

Output:
```
--- Scrape @ Fri May 15 09:50:37 2026 ---
  Mode:        stable
  Uptime:      115s
  Error rate:  0.0%
  P99 latency: 100.0ms
  Chaos:       none

  Policy Compliance:
    Infrastructure: ✅ PASS
    Canary safety:  ✅ PASS
```

---

### `audit`
Generates `audit_report.md` from `history.jsonl` — a full timeline of every deploy, promote, and policy decision.

**Value:** Complete accountability. You can always answer "what happened and why" with a single command.

```bash
python swiftdeploy.py audit
```

---

## OPA Policies

All deployment decisions are made by OPA — the CLI never makes allow/deny decisions itself.

### Infrastructure Policy (pre-deploy)
```rego
allow := true if {
    input.disk_free_gb >= 10
    input.cpu_load <= 2.0
}
```
Blocks deployment if disk free < 10GB or CPU load > 2.0

### Canary Safety Policy (pre-promote)
```rego
allow := true if {
    input.error_rate <= 1.0
    input.p99_latency_ms <= 500
}
```
Blocks canary promotion if error rate > 1% or P99 latency > 500ms

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Welcome message with mode, version, timestamp |
| `/healthz` | GET | Liveness check with uptime in seconds |
| `/chaos` | POST | Inject chaos — slow, error, or recover (canary only) |
| `/metrics` | GET | Prometheus format metrics |

---

## Manifest Reference

```yaml
services:
  image: swift-deploy-1-node:latest
  port: 3000
  mode: stable
  version: v1

nginx:
  image: nginx:latest
  port: 8080
  proxy_timeout: 60

network:
  name: swiftdeploy-net
  driver_type: bridge
```

`manifest.yaml` is the **single source of truth**. All generated files derive from it.

---

## Author
**Edith Asante** — Cloud & DevOps Engineer
## As part of HNG Internship Stage 4
