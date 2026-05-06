from flask import Flask, request, jsonify

import time, random

from collections import defaultdict

app = Flask(__name__)

MODE = "stable"

start_time = time.time()

request_count = defaultdict(int)

request_durations = []

chaos_mode = 0

error_rate = 0

slow_duration = 0

@app.after_request

def add_headers(response):

    if MODE == "canary":

        response.headers["X-Mode"] = "canary"

    return response

@app.route("/")

def home():

    global chaos_mode

    start = time.time()

    if chaos_mode == 1:

        time.sleep(slow_duration)

    if chaos_mode == 2 and random.random() < error_rate:

        request_count[(request.method,"/","500")] += 1

        return jsonify({"error":"chaos"}), 500

    duration = time.time() - start

    request_durations.append(duration)

    request_count[(request.method,"/","200")] += 1

    return jsonify({

        "message":"welcome",

        "mode": MODE,

        "timestamp": time.time()

    })

@app.route("/healthz")

def health():

    request_count[(request.method,"/healthz","200")] += 1

    return jsonify({

        "status":"ok",

        "uptime": int(time.time()-start_time)

    })

@app.route("/chaos", methods=["POST"])

def chaos():

    global chaos_mode, error_rate, slow_duration

    data = request.json

    if data["mode"] == "slow":

        chaos_mode = 1

        slow_duration = data["duration"]

    elif data["mode"] == "error":

        chaos_mode = 2

        error_rate = data["rate"]

    elif data["mode"] == "recover":

        chaos_mode = 0

    return jsonify({"status":"updated"})

@app.route("/metrics")

def metrics():

    uptime = int(time.time() - start_time)

    lines = []

    lines.append(f"app_uptime_seconds {uptime}")

    lines.append(f"app_mode {1 if MODE=='canary' else 0}")

    lines.append(f"chaos_active {chaos_mode}")

    for (method,path,status),count in request_count.items():

        lines.append(

            f'http_requests_total{{method="{method}",path="{path}",status_code="{status}"}} {count}'

        )

    buckets = [0.1,0.3,0.5,1,2,5]

    for b in buckets:

        count = sum(1 for d in request_durations if d <= b)

        lines.append(f'http_request_duration_seconds_bucket{{le="{b}"}} {count}')

    lines.append(f'http_request_duration_seconds_bucket{{le="+Inf"}} {len(request_durations)}')

    return "\n".join(lines), 200, {"Content-Type":"text/plain"}

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=3000)