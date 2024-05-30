from copy import deepcopy
from functools import lru_cache, wraps
import gzip
from hashlib import md5
from itertools import zip_longest
import os
from pathlib import Path
from time import time
from typing import Any
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
                        "country": lambda style: style == "website",
                        "firstName": 1,
                        "lastName": 1,
                        "imageUrl": lambda style: style == "website",
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


def cleanup_rg_data(rg_data, style):
    rg_data = {"matches": deepcopy(rg_data["matches"])}

    def recursive_cleanup(data, schema):
        if isinstance(data, list):
            for item in data:
                recursive_cleanup(item, schema[0])
            return data

        for key in list(data):
            if key not in schema:
                del data[key]
            elif key in schema:
                if isinstance(schema[key], (list, dict)):
                    recursive_cleanup(data[key], schema[key])
                elif callable(schema[key]) and not schema[key](style):
                    del data[key]

        return data

    recursive_cleanup(rg_data, keys_to_keep)
    return rg_data


rg_data = {}
rg_data_timestamp = 0
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))


def get_rg_data(style=None):
    global rg_data, rg_data_timestamp
    if rg_data is not None and time() - rg_data_timestamp < POLLING_INTERVAL:
        return cleanup_rg_data(rg_data, style)

    try:
        req = requests.get("https://www.rolandgarros.com/api/fr-fr/polling", timeout=3)
        rg_data = req.json()
        rg_data_timestamp = time()
        return cleanup_rg_data(rg_data, style)
    except (OSError, ValueError) as err:
        if not rg_data:
            raise ValueError("Can't fetch Roland Garros data") from err
        return rg_data


hashes: dict[str, Any] = {}


def get_hash(obj):
    for hash, test_obj in hashes.items():
        if test_obj == obj:
            return hash

    if len(hashes) > 100:
        for key in list(hashes.keys())[:50]:
            del hashes[key]

    hash = md5(app.json.dumps(obj).encode()).hexdigest()[0:8]
    hashes[hash] = obj
    return hash


def get_diff(obj1, obj2):
    # [added_or_edited, deleted]
    # this must be a list in order to be automatically serialized to JSON by Flask
    ret = [{}, {}]

    def recursive_diff(obj1, obj2, diff):
        if isinstance(obj1, list) and isinstance(obj2, list):
            NOTHING = object()
            for i, (item1, item2) in enumerate(zip_longest(obj1, obj2, fillvalue=NOTHING)):
                if item2 is NOTHING:
                    diff[1][i] = 1
                elif item1 is NOTHING:
                    diff[0][i] = item2
                    continue
                if item1 != item2:  # type: ignore
                    diff[0][i] = {}
                    diff[1][i] = {}
                    recursive_diff(item1, item2, (diff[0][i], diff[1][i]))
                    if diff[0][i] == {}:
                        del diff[0][i]
                    if diff[1][i] == {}:
                        del diff[1][i]
            return

        for key in obj1:
            if key not in obj2:
                diff[1][key] = 1
            else:
                if (
                    isinstance(obj1[key], dict) and isinstance(obj2[key], dict)
                    or isinstance(obj1[key], list) and isinstance(obj2[key], list)
                ):
                    diff[0][key] = {}
                    diff[1][key] = {}
                    recursive_diff(obj1[key], obj2[key], (diff[0][key], diff[1][key]))

                    if diff[0][key] == {}:
                        del diff[0][key]
                    else:
                        keys0 = list(diff[0][key].keys())
                        if keys0 == list(range(len(keys0))):
                            diff[0][key] = list(diff[0][key].values())

                    if diff[1][key] == {}:
                        del diff[1][key]
                    else:
                        keys1 = list(diff[1][key].keys())
                        if keys1 == list(range(len(keys1))):
                            diff[1][key] = list(diff[1][key].values())

                else:
                    if obj1[key] != obj2[key]:
                        diff[0][key] = obj2[key]

        for key in obj2:
            if key not in obj1:
                diff[0][key] = obj2[key]

    recursive_diff(obj1, obj2, ret)
    return ret


def check_hash(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        ret = f(*args, **kwargs)
        ret["hash"] = get_hash(ret)
        expected_hash = request.args.get("hash")

        if ret["hash"] == expected_hash:
            return Response("null", mimetype="application/json")

        if expected_hash and expected_hash in hashes:
            return get_diff(hashes[expected_hash], ret)

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
    return render_template("matches_list.html", match="false")


@app.route("/match/<match_id>")
def match(match_id):
    for match in get_rg_data(request.args.get("style"))["matches"]:
        if match["id"] == match_id:
            break
    else:
        raise NotFound
    return render_template("match.html", match="true", match_id=match_id)


@app.route("/polling")
@check_hash
def polling():
    return get_rg_data(request.args.get("style"))


@app.route("/polling/match/<match_id>")
@check_hash
def polling_match(match_id):
    for match in get_rg_data()["matches"]:
        if match["id"] == match_id:
            return {"matches": [match]}
    raise NotFound


if __name__ == "__main__":
    app.run(debug=True)
