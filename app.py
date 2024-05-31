import gzip
import os
import zlib
from pathlib import Path
from time import time

import requests
from flask import Flask, Response, render_template, request, send_file
from werkzeug.exceptions import NotFound

from cleanup import cleanup_rg_data  # type: ignore
from hashing import check_hash  # type: ignore

app = Flask(__name__)

app.json.ensure_ascii = False  # type: ignore
app.json.compact = True  # type: ignore

Response.default_mimetype = None
Response.automatically_set_content_length = False


@app.after_request
def compress(response: Response):
    """Compress all outcoming responses with deflate or gzip, depending on browser support."""
    try:
        content = response.data
    except RuntimeError:
        # can't get data because it's a stream
        # stop here
        return response

    accept_encoding = request.headers.get("Accept-Encoding", "")

    if "deflate" in accept_encoding:
        content = zlib.compress(content, 5)
        response.content_encoding = "deflate"
    elif "gzip" in accept_encoding:
        content = gzip.compress(content, 5)
        response.content_encoding = "gzip"

    response.data = content
    # don't remove Content-Length because it automatically
    # adds Transfer-Encoding: chunked, which is longer
    response.content_length = len(content)

    return response


rg_data = {}  # data from the server
rg_data_timestamp = 0  # last polling date  # pylint: disable=C0103
# minimum polling interval
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))


def get_rg_data(style=None):
    """
    Return information from the Roland-Garros server suitable for the given display `style`.
    The data may have been cached.
    """
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
        return cleanup_rg_data(rg_data, style)


@app.route("/static/cdn.min.js")
def alpinejs():
    """Alpine.js (for local development)"""
    alpinejs_path = Path(__file__).parent / "static/cdn.min.js"
    # if the file exists, send it
    if alpinejs_path.exists():
        return send_file(alpinejs_path, mimetype="text/javascript")

    # otherwise, download it and serve it
    req = requests.get("https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js")
    return Response(req.text, mimetype="text/javascript")


@app.route("/favicon.png")
def favicon_png():
    """PNG favicon"""
    return send_file(Path(__file__).parent / "static/favicon.png")


@app.route("/favicon.ico")
def favicon_ico():
    """ICO favicon"""
    return send_file(Path(__file__).parent / "static/favicon.ico")


@app.route("/")
def index():
    """Homepage with matches list"""
    return render_template("matches_list.html", match="false")


@app.route("/match/<match_id>")
def match_page(match_id):
    """Match page"""
    for match in get_rg_data(request.args.get("style"))["matches"]:
        if match["id"] == match_id:
            break
    else:
        raise NotFound
    return render_template("match.html", match="true", match_id=match_id)


@app.route("/polling")
@check_hash
def polling():
    """Polling endpoint for the home page"""
    return get_rg_data(request.args.get("style"))


@app.route("/polling/match/<match_id>")
@check_hash
def polling_match(match_id):
    """Polling endpoint for the match pages"""
    for match in get_rg_data(request.args.get("style"))["matches"]:
        if match["id"] == match_id:
            return {"matches": [match]}
    raise NotFound


if __name__ == "__main__":
    app.run(debug=True)
