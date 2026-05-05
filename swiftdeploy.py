import yaml

import os

import subprocess

import socket

import time

import requests

from jinja2 import Template

# -----------------------------

# LOAD & SAVE MANIFEST

# -----------------------------

def load_manifest():

    with open("manifest.yaml") as f:

        return yaml.safe_load(f)

def save_manifest(data):

    with open("manifest.yaml", "w") as f:

        yaml.dump(data, f)

# -----------------------------

# TEMPLATE RENDER

# -----------------------------

def render_template(template_path, output_path, data):

    with open(template_path) as f:

        content = Template(f.read()).render(data)

    with open(output_path, "w") as f:

        f.write(content)

# -----------------------------

# INIT

# -----------------------------

def init():

    data = load_manifest()

    render_template("templates/nginx.conf.tpl", "nginx.conf", data)

    render_template("templates/docker-compose.yml.tpl", "docker-compose.yml", data)

    print("✅ Config files generated")

# -----------------------------

# VALIDATE

# -----------------------------

def validate():

    print("Running validation...\n")

    # CHECK 1

    if not os.path.exists("manifest.yaml"):

        print("❌ FAIL: manifest.yaml missing")

        exit(1)

    try:

        data = load_manifest()

        print("✅ PASS: manifest.yaml valid")

    except Exception:

        print("❌ FAIL: invalid YAML")

        exit(1)

    # CHECK 2

    try:

        assert data["services"]["image"]

        assert data["services"]["port"]

        assert data["nginx"]["image"]

        assert data["nginx"]["port"]

        assert data["network"]["name"]

        assert data["network"]["driver_type"]

        print("✅ PASS: required fields present")

    except Exception:

        print("❌ FAIL: missing required fields")

        exit(1)

    # CHECK 3

    result = subprocess.run(

        ["docker", "images", "-q", data["services"]["image"]],

        capture_output=True,

        text=True

    )

    if result.stdout.strip() == "":

        print("❌ FAIL: docker image not found")

        exit(1)

    else:

        print("✅ PASS: docker image exists")

    # CHECK 4

    s = socket.socket()

    try:

        s.bind(("localhost", data["nginx"]["port"]))

        s.close()

        print("✅ PASS: nginx port free")

    except Exception:

        print("❌ FAIL: port already in use")

        exit(1)

    # CHECK 5

    try:

        subprocess.run(

            ["docker", "compose", "up", "-d"],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL

        )

        result = subprocess.run(

            ["docker", "compose", "exec", "-T", "nginx", "nginx", "-t"],

            capture_output=True,

            text=True

        )

        if "successful" in result.stdout.lower() or "successful" in result.stderr.lower():

            print("✅ PASS: nginx.conf valid")

        else:

            print("❌ FAIL: nginx.conf invalid")

            print(result.stderr)

            exit(1)

    finally:

        subprocess.run(

            ["docker", "compose", "down"],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL

        )

    print("\n🎉 ALL CHECKS PASSED")

# -----------------------------

# DEPLOY

# -----------------------------

def deploy():

    print("🚀 Deploying...\n")

    init()

    subprocess.run(["docker", "compose", "up", "-d"])

    start = time.time()

    while time.time() - start < 60:

        try:

            r = requests.get("http://localhost:8080/healthz")

            if r.status_code == 200:

                print("✅ Deployment successful")

                return

        except Exception:

            pass

        time.sleep(2)

    print("❌ Deployment timeout")

    exit(1)

# -----------------------------

# PROMOTE

# -----------------------------

def promote(mode):

    if mode not in ["canary", "stable"]:

        print("❌ Invalid mode")

        exit(1)

    data = load_manifest()

    data["services"]["mode"] = mode

    save_manifest(data)
    print(f"🔁 Switching to {mode} mode...")

    init()

    subprocess.run(

        ["docker", "compose", "up", "-d", "--no-deps", "--build", "app"]

    )

    time.sleep(5)

    try:

        r = requests.get("http://localhost:8080/healthz")

        if r.status_code == 200:

            print(f"✅ Promotion to {mode} successful")

        else:

            print("❌ Health check failed after promotion")

    except Exception:

        print("❌ Unable to verify service")

# -----------------------------

# TEARDOWN

# -----------------------------

def teardown(clean=False):

    print("🧹 Tearing down...")

    subprocess.run(["docker", "compose", "down", "-v"])

    if clean:

        if os.path.exists("nginx.conf"):

            os.remove("nginx.conf")

        if os.path.exists("docker-compose.yml"):

            os.remove("docker-compose.yml")

        print("🧼 Cleaned generated files")

    print("✅ Teardown complete")

# -----------------------------

# MAIN

# -----------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print("Usage: python swiftdeploy.py <command>")

        exit(1)

    command = sys.argv[1]

    if command == "init":

        init()

    elif command == "validate":

        validate()

    elif command == "deploy":

        deploy()

    elif command == "promote":

        if len(sys.argv) < 3:

            print("Usage: promote [canary|stable]")

            exit(1)

        promote(sys.argv[2])

    elif command == "teardown":

        clean = "--clean" in sys.argv

        teardown(clean)

    else:

        print("Unknown command")