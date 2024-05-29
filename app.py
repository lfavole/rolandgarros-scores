from copy import deepcopy
from functools import wraps
import gzip
from hashlib import md5
import os
from pathlib import Path
from time import time
import zlib
from flask import Flask, Response, render_template, request, send_file
import requests
from werkzeug.exceptions import NotFound

app = Flask(__name__)

app.json.ensure_ascii = False  # type: ignore
app.json.compact = True  # type: ignore


@app.after_request
def compress(response):
    try:
        content = response.data
    except RuntimeError:
        # Can't get data because it's a stream
        return response

    accept_encoding = request.headers.get("Accept-Encoding", "")

    if "deflate" in accept_encoding:
        content = zlib.compress(content, 5)
        response.headers["Content-Encoding"] = "deflate"
    elif "gzip" in accept_encoding:
        content = gzip.compress(content, 5)
        response.headers["Content-Encoding"] = "gzip"

    response.data = content
    response.headers["Content-Length"] = len(content)
    return response


keys_to_keep = {
    "test": 1,
    "matches": [
        {
            "id": 1,
            "matchData": {
                "courtName": 1,
                "dateSchedule": 1,
                "durationInMinutes": 1,
                "isNightSession": 1,
                "notBefore": 1,
                "roundLabel": 1,
                "startingAt": 1,
                "status": 1,
                "typeLabel": 1,
            },
            "teamA": {
                "endCause": 1,
                "hasService": 1,
                "players": [
                    {
                        "firstName": 1,
                        "lastName": 1,
                    }
                ],
                "points": 1,
                "seed": 1,
                "sets": [
                    {
                        "inProgress": 1,
                        "score": 1,
                        "tieBreak": 1,
                        "winner": 1,
                    }
                ],
                "winner": 1,
            },
        }
    ]
}
keys_to_keep["matches"][0]["teamB"] = keys_to_keep["matches"][0]["teamA"]


def cleanup_rg_data(rg_data):
    rg_data = {"matches": deepcopy(rg_data["matches"])}

    def recursive_cleanup(data, schema):
        if isinstance(data, list):
            for item in data:
                recursive_cleanup(item, schema[0])
            return data

        for key in list(data):
            if key not in schema:
                del data[key]
            elif key in schema and isinstance(schema[key], (list, dict)):
                recursive_cleanup(data[key], schema[key])

        return data

    recursive_cleanup(rg_data, keys_to_keep)
    return rg_data


rg_data = {}
rg_data_timestamp = 0
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))


def get_rg_data():
    global rg_data, rg_data_timestamp
    if rg_data is not None and time() - rg_data_timestamp < POLLING_INTERVAL:
        return rg_data

    try:
        req = requests.get("https://www.rolandgarros.com/api/fr-fr/polling", timeout=3)
        rg_data = cleanup_rg_data(req.json())
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
        ret["hash"] = md5(app.json.dumps(ret).encode()).hexdigest()[0:8]
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
