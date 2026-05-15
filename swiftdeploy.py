import os
import sys
import json
import requests
import time
import subprocess
import shutil
import yaml
import psutil
import socket

OPA_URL = "http://localhost:8181/v1/data"
METRICS_URL = "http://localhost:8080/metrics"
APP_URL = "http://localhost:8080"
HISTORY_FILE = "history.jsonl"
AUDIT_REPORT = "audit_report.md"
MANIFEST_FILE = "manifest.yaml"

def load_manifest():
    with open(MANIFEST_FILE, "r") as f:
        return yaml.safe_load(f)

def write_history(event):
    event["timestamp"] = time.time()
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

def check_opa():
    try:
        r = requests.get("http://localhost:8181/health", timeout=2)
        return r.status_code == 200
    except:
        return False

def query_opa(policy_path, input_data):
    try:
        url = f"{OPA_URL}/{policy_path}"
        r = requests.post(url, json={"input": input_data}, timeout=5)
        if r.status_code == 200:
            result = r.json().get("result", {}); return result if isinstance(result, dict) else {"allow": result, "reason": ""}
        return {"allow": False, "reason": f"OPA returned status {r.status_code}"}
    except requests.exceptions.ConnectionError:
        print("? OPA is unavailable. Cannot proceed without policy validation.")
        sys.exit(1)
    except Exception as e:
        print(f"? OPA query failed: {e}")
        sys.exit(1)

def get_host_stats():
    disk = shutil.disk_usage("/")
    disk_free_gb = disk.free / (1024 ** 3)
    cpu_load = psutil.cpu_percent() / 100
    mem = psutil.virtual_memory()
    return {
        "disk_free_gb": round(disk_free_gb, 2),
        "cpu_load": round(cpu_load, 2),
        "mem_percent": round(mem.percent, 2)
    }

def scrape_metrics():
    try:
        r = requests.get(METRICS_URL, timeout=5)
        if r.status_code != 200:
            return None
        metrics = {}
        for line in r.text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                metrics[parts[0]] = float(parts[1])
        return metrics
    except:
        return None

def calc_error_rate(metrics):
    total = 0
    errors = 0
    for key, val in metrics.items():
        if key.startswith("http_requests_total"):
            total += val
            if 'status_code="5' in key:
                errors += val
    if total == 0:
        return 0.0
    return round((errors / total) * 100, 2)

def calc_p99_latency(metrics):
    buckets = []
    for key, val in metrics.items():
        if "http_request_duration_seconds_bucket" in key and 'le="' in key:
            le = float(key.split('le="')[1].split('"')[0]) if '+Inf' not in key else 999
            buckets.append((le, val))
    if not buckets:
        return 0.0
    buckets.sort()
    total = buckets[-1][1] if buckets else 0
    p99_threshold = total * 0.99
    for le, count in buckets:
        if count >= p99_threshold:
            return le * 1000
    return 0.0

def init():
    manifest = load_manifest()
    with open("templates/nginx.conf.tpl", "r") as f:
        nginx_tpl = f.read()
    with open("templates/docker-compose.yml.tpl", "r") as f:
        compose_tpl = f.read()
    nginx_out = nginx_tpl.replace("{{ nginx_port }}", str(manifest["nginx"]["port"]))
    nginx_out = nginx_out.replace("{{ app_port }}", str(manifest["services"]["port"]))
    nginx_out = nginx_out.replace("{{ proxy_timeout }}", str(manifest["nginx"].get("proxy_timeout", 30)))
    compose_out = compose_tpl.replace("{{ app_image }}", manifest["services"]["image"])
    compose_out = compose_out.replace("{{ app_port }}", str(manifest["services"]["port"]))
    compose_out = compose_out.replace("{{ nginx_image }}", manifest["nginx"]["image"])
    compose_out = compose_out.replace("{{ nginx_port }}", str(manifest["nginx"]["port"]))
    compose_out = compose_out.replace("{{ network_name }}", manifest["network"]["name"])
    compose_out = compose_out.replace("{{ network_driver }}", manifest["network"]["driver_type"])
    compose_out = compose_out.replace("{{ mode }}", manifest["services"].get("mode", "stable"))
    compose_out = compose_out.replace("{{ version }}", str(manifest["services"].get("version", "1.0")))
    with open("nginx.conf", "w") as f:
        f.write(nginx_out)
    with open("docker-compose.yml", "w") as f:
        f.write(compose_out)
    write_history({"event": "init", "status": "success"})
    print("? Config files generated successfully")

def validate():
    manifest = load_manifest()
    failed = 0
    try:
        if manifest:
            print("? [1/5] manifest.yaml exists and is valid YAML")
        else:
            print("? [1/5] manifest.yaml is empty")
            failed += 1
    except Exception as e:
        print(f"? [1/5] manifest.yaml invalid: {e}")
        failed += 1
    required = ["services", "nginx", "network"]
    missing = [f for f in required if f not in manifest]
    if not missing:
        print("? [2/5] All required fields present")
    else:
        print(f"? [2/5] Missing fields: {missing}")
        failed += 1
    image = manifest["services"]["image"]
    result = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
    if result.returncode == 0:
        print(f"? [3/5] Docker image '{image}' exists locally")
    else:
        print(f"? [3/5] Docker image '{image}' not found locally")
        failed += 1
    nginx_port = int(manifest["nginx"]["port"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result_code = sock.connect_ex(("localhost", nginx_port))
    sock.close()
    if result_code != 0:
        print(f"? [4/5] Nginx port {nginx_port} is available")
    else:
        print(f"? [4/5] Nginx port {nginx_port} is already in use")
        failed += 1
    if os.path.exists("nginx.conf"):
        print("? [5/5] nginx.conf exists")
    else:
        print("? [5/5] nginx.conf not found — run init first")
        failed += 1
    print(f"\n{'? All checks passed!' if failed == 0 else f'? {failed} check(s) failed'}")
    if failed > 0:
        sys.exit(1)

def pre_deploy_check():
    print("?? Running pre-deploy policy check...")
    if not check_opa():
        print("? OPA is unavailable. Cannot validate policies.")
        print("   Start OPA with: docker compose up -d opa")
        sys.exit(1)
    stats = get_host_stats()
    print(f"   Disk free: {stats['disk_free_gb']}GB | CPU: {stats['cpu_load']} | Memory: {stats['mem_percent']}%")
    result = query_opa("infra/allow", stats)
    allowed = result.get("allow", False)
    reason = result.get("reason", "No reason provided")
    write_history({"event": "pre_deploy_check", "input": stats, "result": result})
    if allowed:
        print("? Infrastructure policy: PASSED")
    else:
        print(f"? Infrastructure policy: BLOCKED")
        print(f"   Reason: {reason}")
        sys.exit(1)

def deploy():
    init()
    pre_deploy_check()
    print("?? Deploying stack...")
    os.system("docker compose up -d")
    print("? Waiting for /healthz...")
    for i in range(12):
        time.sleep(5)
        try:
            r = requests.get(f"{APP_URL}/healthz", timeout=3)
            if r.status_code == 200:
                print("? Deployment successful — service is healthy")
                write_history({"event": "deploy", "status": "success"})
                return
        except:
            pass
        print(f"   Attempt {i+1}/12...")
    print("? Deployment failed — health check timed out")
    write_history({"event": "deploy", "status": "failed"})
    sys.exit(1)

def promote(mode):
    if mode not in ["canary", "stable"]:
        print("? Usage: python swiftdeploy.py promote [canary|stable]")
        sys.exit(1)
    if mode == "canary":
        print("?? Running pre-promote policy check...")
        if not check_opa():
            print("? OPA unavailable. Cannot validate canary safety.")
            sys.exit(1)
        metrics = scrape_metrics()
        if not metrics:
            print("? Cannot scrape /metrics for canary safety check")
            sys.exit(1)
        error_rate = calc_error_rate(metrics)
        p99 = calc_p99_latency(metrics)
        input_data = {"error_rate": error_rate, "p99_latency_ms": p99}
        print(f"   Error rate: {error_rate}% | P99 latency: {p99}ms")
        result = query_opa("canary", input_data)
        allowed = result.get("allow", False)
        reason = result.get("reason", "No reason provided")
        write_history({"event": "pre_promote_check", "input": input_data, "result": result})
        if not allowed:
            print(f"? Canary safety policy: BLOCKED")
            print(f"   Reason: {reason}")
            sys.exit(1)
        print("? Canary safety policy: PASSED")
    manifest = load_manifest()
    manifest["services"]["mode"] = mode
    with open(MANIFEST_FILE, "w") as f:
        yaml.dump(manifest, f)
    init()
    print(f"?? Switching to {mode} mode...")
    os.system("docker compose up -d --no-deps app")
    time.sleep(5)
    try:
        r = requests.get(f"{APP_URL}/healthz", timeout=5)
        if r.status_code == 200:
            print(f"? Promote to {mode} successful")
            write_history({"event": "promote", "mode": mode, "status": "success"})
    except Exception as e:
        print(f"? Could not confirm new mode: {e}")

def teardown(clean=False):
    print("?? Tearing down stack...")
    os.system("docker compose down -v")
    write_history({"event": "teardown", "clean": clean})
    if clean:
        for f in ["nginx.conf", "docker-compose.yml"]:
            if os.path.exists(f):
                os.remove(f)
                print(f"???  Deleted {f}")
    print("? Teardown complete")

def status():
    print("?? Monitoring Status (Ctrl+C to stop)...")
    try:
        while True:
            metrics = scrape_metrics()
            print(f"\n--- Scrape @ {time.ctime()} ---")
            if metrics:
                error_rate = calc_error_rate(metrics)
                p99 = calc_p99_latency(metrics)
                mode = "canary" if metrics.get("app_mode", 0) == 1 else "stable"
                chaos = metrics.get("chaos_active", 0)
                print(f"  Mode:        {mode}")
                print(f"  Uptime:      {metrics.get('app_uptime_seconds', 0):.0f}s")
                print(f"  Error rate:  {error_rate}%")
                print(f"  P99 latency: {p99}ms")
                print(f"  Chaos:       {'active' if chaos > 0 else 'none'}")
                print("\n  Policy Compliance:")
                if check_opa():
                    stats = get_host_stats()
                    infra = query_opa("infra/allow", stats)
                    print(f"    Infrastructure: {'? PASS' if infra.get('allow') else '? FAIL - ' + str(infra.get('reason',''))}")
                    canary_data = {"error_rate": error_rate, "p99_latency_ms": p99}
                    canary = query_opa("canary/allow", canary_data)
                    print(f"    Canary safety:  {'? PASS' if canary.get('allow') else '? FAIL - ' + str(canary.get('reason',''))}")
                else:
                    print("    OPA unavailable — policy compliance unknown")
                write_history({"event": "status_scrape", "mode": mode, "error_rate": error_rate, "p99_latency_ms": p99, "chaos_active": chaos})
            else:
                print("  ??  Metrics unavailable — is the stack running?")
                write_history({"event": "status_scrape", "error": "metrics_unavailable"})
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n?? Stopped.")

def audit():
    print("?? Generating Audit Report...")
    if not os.path.exists(HISTORY_FILE):
        print("? No history found. Run deploy or status first.")
        return
    with open(HISTORY_FILE, "r") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    with open(AUDIT_REPORT, "w") as out:
        out.write("# SwiftDeploy Audit Report\n\n")
        out.write(f"Generated: {time.ctime()}\n\n")
        out.write("## Timeline\n\n")
        out.write("| Time | Event | Details |\n")
        out.write("|---|---|---|\n")
        for entry in lines:
            ts = time.ctime(entry.get("timestamp", 0))
            event = entry.get("event", "unknown")
            details = ""
            if event == "deploy":
                details = f"status={entry.get('status')}"
            elif event == "promote":
                details = f"mode={entry.get('mode')} status={entry.get('status')}"
            elif event == "status_scrape":
                details = f"mode={entry.get('mode','?')} error_rate={entry.get('error_rate','?')}% p99={entry.get('p99_latency_ms','?')}ms"
            elif event in ["pre_deploy_check", "pre_promote_check"]:
                result = entry.get("result", {})
                status = "PASSED" if result.get("allow") else "BLOCKED"
                details = f"{status} | reason={result.get('reason','')}"
            out.write(f"| {ts} | {event} | {details} |\n")
        violations = [e for e in lines if e.get("event") in ["pre_deploy_check", "pre_promote_check"] and not e.get("result", {}).get("allow", True)]
        out.write("\n## Policy Violations\n\n")
        if violations:
            out.write("| Time | Check | Reason |\n")
            out.write("|---|---|---|\n")
            for v in violations:
                ts = time.ctime(v.get("timestamp", 0))
                check = v.get("event")
                reason = v.get("result", {}).get("reason", "unknown")
                out.write(f"| {ts} | {check} | {reason} |\n")
        else:
            out.write("No policy violations recorded.\n")
    print(f"? Report generated: {AUDIT_REPORT}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python swiftdeploy.py [init|validate|deploy|promote|teardown|status|audit]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "init": init()
    elif cmd == "validate": validate()
    elif cmd == "deploy": deploy()
    elif cmd == "promote":
        if len(sys.argv) < 3:
            print("Usage: python swiftdeploy.py promote [canary|stable]")
            sys.exit(1)
        promote(sys.argv[2])
    elif cmd == "teardown":
        clean = "--clean" in sys.argv
        teardown(clean)
    elif cmd == "status": status()
    elif cmd == "audit": audit()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python swiftdeploy.py [init|validate|deploy|promote|teardown|status|audit]")
        sys.exit(1)




