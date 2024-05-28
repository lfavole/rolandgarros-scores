import os
from pathlib import Path
from time import time
from flask import Flask, Response, render_template, send_file
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
        return rg_data
    except (OSError, ValueError) as err:
        if not rg_data:
            raise ValueError("Can't fetch Roland Garros data") from err
        return rg_data


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
def polling():
    return get_rg_data()


@app.route("/polling/match/<match_id>")
def polling_match(match_id):
    for match in get_rg_data()["matches"]:
        if match["id"] == match_id:
            return {"matches": [match]}
    raise NotFound


if __name__ == "__main__":
    app.run(debug=True)
