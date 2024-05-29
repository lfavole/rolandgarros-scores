from functools import wraps
from hashlib import md5
import json
import os
from pathlib import Path
from time import time
from flask import Flask, Response, render_template, request, send_file
import requests
from werkzeug.exceptions import NotFound

app = Flask(__name__)

rg_data = {}
rg_data_timestamp = 0
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))


def get_rg_data():
    global rg_data, rg_data_timestamp
    if rg_data is not None and time() - rg_data_timestamp < POLLING_INTERVAL:
        return rg_data

    try:
        req = requests.get("https://www.rolandgarros.com/api/fr-fr/polling", timeout=3)
        rg_data = req.json()
        rg_data_timestamp = time()
        return rg_data
    except (OSError, ValueError) as err:
        if not rg_data:
            raise ValueError("Can't fetch Roland Garros data") from err
        return rg_data


def check_hash(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        ret = f(*args, **kwargs)
        ret["hash"] = md5(json.dumps(ret).encode()).hexdigest()[0:8]
        print(ret["hash"], request.args.get("hash"))
        if ret["hash"] == request.args.get("hash"):
            return Response("null", mimetype="application/json")
        return ret

    return decorator


@app.route("/static/cdn.min.js")
def alpinejs():
    alpinejs_path = Path(__file__).parent / "static/cdn.min.js"
    if alpinejs_path.exists():
        return send_file(alpinejs_path, mimetype="text/javascript")

    req = requests.get("https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js")
    return Response(req.text, mimetype="text/javascript")


@app.route("/")
def index():
    return render_template("matches_list.html")


@app.route("/match/<match_id>")
def match(match_id):
    for match in get_rg_data()["matches"]:
        if match["id"] == match_id:
            break
    else:
        raise NotFound
    return render_template("match.html", match_id=match_id)


@app.route("/polling")
@check_hash
def polling():
    return get_rg_data()


@app.route("/polling/match/<match_id>")
@check_hash
def polling_match(match_id):
    for match in get_rg_data()["matches"]:
        if match["id"] == match_id:
            return {"matches": [match]}
    raise NotFound


if __name__ == "__main__":
    app.run(debug=True)
