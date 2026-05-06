import os
import sys
import json
import requests
import time
import shutil

# CONFIGURATION - Matches your Docker/OPA setup
OPA_URL = "http://localhost:8181/v1/data"
METRICS_URL = "http://localhost:8000/metrics"
HISTORY_FILE = "history.jsonl"
AUDIT_REPORT = "audit_report.md"

def init():
    """Requirement: Initialize the environment and policies directory."""
    if not os.path.exists("policies"):
        os.makedirs("policies")
        print("📁 Created policies directory.")
    # Create empty history file if it doesn't exist to prevent audit crashes
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            f.write(json.dumps({"event": "init", "time": time.time()}) + "\n")
    print("✅ Initialization complete.")

def check_opa():
    """Check if OPA sidecar is reachable."""
    try:
        response = requests.get("http://localhost:8181/v1/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def pre_deploy():
    """Requirement 3A: Pre-deploy policy check."""
    if not check_opa():
        print("❌ OPA unavailable - cannot validate policies. Safety halt.")
        return False

    total, used, free = shutil.disk_usage("/")
    data = {
        "input": {
            "disk_free": free / (1024**3), # GB
            "cpu_load": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.5,
            "thresholds": {"disk_min": 10, "cpu_max": 2.0}
        }
    }

    try:
        res = requests.post(f"{OPA_URL}/infra", json=data).json()
        decision = res.get("result", {})
        if decision.get("allow", False):
            print("✅ Policy Check Passed: Infrastructure is healthy.")
            return True
        else:
            reason = decision.get("reason", "Unknown policy violation")
            print(f"❌ BLOCKED: {reason}")
            return False
    except Exception as e:
        print(f"❌ Policy Engine Error: {e}")
        return False

def deploy():
    if not pre_deploy():
        return
    print("🚀 Deploying services...")
    os.system("docker compose up -d")

def status():
    """Requirement 3B: Real-time dashboard and history logging."""
    print("📋 Monitoring Status (Ctrl+C to stop)...")
    while True:
        try:
            r = requests.get(METRICS_URL, timeout=3)
            metrics_text = r.text
            print(f"\n--- Scrape @ {time.ctime()} ---\n{metrics_text[:150]}...")
            
            with open(HISTORY_FILE, "a") as f:
                f.write(json.dumps({"timestamp": time.time(), "metrics": metrics_text}) + "\n")
        except Exception as e:
            print(f"⚠️ Metrics unavailable: {e}")
        time.sleep(5)

def audit():
    """Requirement 3C: Generate audit_report.md from history."""
    print("📝 Generating Audit Report...")
    if not os.path.exists(HISTORY_FILE):
        print("❌ No history found. Run 'status' first.")
        return

    with open(HISTORY_FILE, "r") as f:
        lines = f.readlines()

    with open(AUDIT_REPORT, "w") as out:
        out.write("# SwiftDeploy Audit Report\n\n")
        out.write("| Timestamp | Status | Metric Snippet |\n")
        out.write("|-----------|--------|----------------|\n")
        for line in lines[-20:]: # Last 20 scrapes
            entry = json.loads(line)
            ts = time.ctime(entry.get('timestamp', time.time()))
            snippet = entry.get('metrics', 'N/A')[:40].replace('\n', ' ')
            out.write(f"| {ts} | Active | {snippet}... |\n")
    print(f"✅ Report generated: {AUDIT_REPORT}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python swiftdeploy.py [init|deploy|status|audit]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        init()
    elif cmd == "deploy":
        deploy()
    elif cmd == "status":
        status()
    elif cmd == "audit":
        audit()
    else:
        print(f"Unknown command: {cmd}")