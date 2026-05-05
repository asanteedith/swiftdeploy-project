from flask import Flask, request, jsonify

import os, time, random

app = Flask(__name__)

MODE = os.getenv("MODE", "stable")

APP_VERSION = os.getenv("APP_VERSION", "v1")

START = time.time()

CHAOS = {"mode": None, "rate": 0}

@app.route("/")

def home():

    return jsonify({

        "message": "welcome",

        "mode": MODE,

        "version": APP_VERSION,

        "timestamp": time.time()

    })

@app.route("/healthz")

def health():

    return jsonify({

        "status": "ok",

        "uptime": int(time.time() - START)

    })

@app.route("/chaos", methods=["POST"])

def chaos():

    global CHAOS

    if MODE != "canary":

        return jsonify({"error": "not allowed"}), 403

    data = request.json

    if data["mode"] == "slow":

        time.sleep(data.get("duration", 1))

    elif data["mode"] == "error":

        CHAOS = {"mode": "error", "rate": data.get("rate", 0.5)}

    elif data["mode"] == "recover":

        CHAOS = {"mode": None, "rate": 0}

    return jsonify({"status": "updated"})

@app.before_request

def inject():

    if CHAOS["mode"] == "error":

        if random.random() < CHAOS["rate"]:

            return jsonify({"error": "failure"}), 500

@app.after_request

def headers(resp):

    if MODE == "canary":

        resp.headers["X-Mode"] = "canary"

    return resp

app.run(host="0.0.0.0", port=3000)