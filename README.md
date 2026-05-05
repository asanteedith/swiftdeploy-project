Live Demo: http://localhost:8080
# SwiftDeploy Project

SwiftDeploy is a CLI tool that builds, deploys, and manages a containerized application stack from a single declarative manifest.yaml.
Instead of manually configuring infrastructure, SwiftDeploy generates all required configurations and controls the lifecycle of the system.

⸻


# Project Overview
This project implements:
 • Declarative infrastructure using YAML
 • Automatic generation of:
 ◦ nginx.conf
 ◦ docker-compose.yml
 • Container lifecycle management
 • Canary and stable deployment modes
 • Health checks and validation


manifest.yaml

      ↓

swiftdeploy CLI

      ↓

nginx.conf + docker-compose.yml

      ↓

Docker Compose

      ↓

Nginx → API ServiceArchitecture



⸻


# Project Structure
swiftdeploy-project/

│

├── manifest.yaml

├── swiftdeploy.py

├── nginx.conf

├── docker-compose.yml

│

├── app/

│   ├── main.py

│   └── Dockerfile

│

├── templates/

│   ├── nginx.conf.tpl

│   └── docker-compose.yml.tpl

│

└── README.md

⸻


 # Setup

Requirements

Python 
Docker & Docker Compose

⸻


# Install dependencies
pip install pyyaml jinja2 requests

⸻

# Usage

1. Generate configuration files
python swiftdeploy.py init

⸻


# 2. Validate setup

Runs 5 pre-flight checks:

manifest validity
required fields
docker image existence
nginx port availability
nginx configuration validity

python swiftdeploy.py validate

⸻


# 3. Deploy stack
 • Generates configs
 • Starts containers
 • Waits for /healthz (max 60s)

python swiftdeploy.py deploy

⸻


# 4. Promote deployment

Switch to canary mode
python swiftdeploy.py promote canary

Switch back to stable
python swiftdeploy.py promote stable

⸻


 # 5. Teardown

Stops and removes all resources:
python swiftdeploy.py teardown
Remove generated files as well:

python swiftdeploy.py teardown --clean

⸻


# API Endpoints
GET 
/
Returns:
 • message
 • mode (stable/canary)
 • version
 • timestamp



GET 
/healthz
Returns:
 • status
 • uptime (seconds)



POST 
/chaos
(canary only)


⸻

# Simulates failures:

# • Slow response:

 { "mode": "slow", "duration": 3 }


 # Random errors:
 { "mode": "error", "rate": 0.5 }

 # Recover
 { "mode": "recover" }

 ⸻


  # Deployment Modes

 • Stable → normal operation
 • Canary → adds X-Mode: canary header and enables chaos testing


 ⸻



# Notes
 • manifest.yaml is the single source of truth
 • Generated files must not be edited manually
 • All infrastructure is derived from the manifest



# ✅ Validation Checklist
 • init regenerates configs
 • validate passes all checks
 • deploy succeeds
 • promote canary/stable works
 • teardown --clean works

 ⸻



# Submission
Include:
 • Validation output
 • Deployment output
 • Promotion confirmation
 • Generated configs
 • Nginx access logs

 ⸻



 # Author
Built as part of the HNG DevOps Stage 4A task.


