import gzip
import os
import subprocess as sp
import zlib
from collections import defaultdict
from pathlib import Path
from time import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import minify_html
import requests
from flask import Flask, Response, redirect, render_template, request, send_file, url_for
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import NotFound

from cleanup import cleanup_rg_data  # type: ignore
from hashing import check_hash  # type: ignore

app = Flask(__name__)

class JSONProvider(DefaultJSONProvider):
    def dumps(self, *args, **kwargs) -> str:
        if (self.compact is None and self._app.debug) or self.compact is False:
            kwargs.setdefault("indent", 2)
        else:
            kwargs.setdefault("separators", (",", ":"))
        return super().dumps(*args, **kwargs)

app.json = JSONProvider(app)

app.json.ensure_ascii = False  # type: ignore
app.json.compact = True  # type: ignore

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

    if response.content_type.split(";")[0] == "text/html":
        try:
            content = minify_html.minify(content.decode("utf-8")).encode("utf-8")
        except:
            pass

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


rg_data: dict[str, (dict | None, int)] = defaultdict(lambda: (None, 0))  # data from the server
rg_data_timestamp = 0  # last polling date  # pylint: disable=C0103
# minimum polling interval
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))


def get_rg_data(endpoint="polling", style=None):
    """
    Return information from the Roland-Garros server suitable for the given display `style`.
    The data may have been cached.
    """
    if rg_data[endpoint][0] is not None and time() - rg_data[endpoint][1] < POLLING_INTERVAL:
        return cleanup_rg_data(endpoint, rg_data[endpoint][0], style)

    try:
        req = requests.get("https://www.rolandgarros.com/api/fr-fr/" + endpoint.replace("?meta=1", ""), timeout=3)
        rg_data[endpoint] = (req.json(), time())
        return cleanup_rg_data(endpoint, rg_data[endpoint][0], style)
    except (OSError, ValueError) as err:
        if rg_data[endpoint][0] is None:
            raise ValueError("Can't fetch Roland-Garros data") from err
        return cleanup_rg_data(endpoint, rg_data[endpoint][0], style)


def proxy(url):
    """Proxy a request to a given URL"""
    req = requests.get(url)
    if req.status_code == 404:
        raise NotFound
    return Response(req.content, mimetype=req.headers["Content-Type"])


@app.route("/sw.js")
def sw():
    """Service worker"""
    sw_path = Path(__file__).parent / "static/sw.js"
    sw_content = sw_path.read_text("utf-8")
    commit = os.environ.get("VERCEL_GIT_COMMIT_SHA")
    if not commit:
        try:
            if sp.call(["git", "diff-index", "--quiet", "HEAD", "--"], cwd=Path(__file__).parent, stdout=sp.DEVNULL) == 0:
                commit = commit or sp.check_output(["git", "describe", "HEAD", "--abbrev=8", "--always"], cwd=Path(__file__).parent, text=True).rstrip("\n")
        except sp.CalledProcessError:
            pass
    commit = commit or "dev"
    sw_content = sw_content.replace('"dev"', f'"{commit[:8]}"', 1)
    return Response(sw_content, mimetype="text/javascript")


@app.route("/static/cdn.min.js")
def alpinejs():
    """Alpine.js (for local development)"""
    alpinejs_path = Path(__file__).parent / "static/cdn.min.js"
    # if the file exists, send it
    if alpinejs_path.exists():
        return send_file(alpinejs_path, mimetype="text/javascript")

    # otherwise, download it and serve it
    return proxy("https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js")


@app.route("/static/persist.min.js")
def persist():
    """Alpine.js persist plugin (for local development)"""
    persist_path = Path(__file__).parent / "static/persist.min.js"
    # if the file exists, send it
    if persist_path.exists():
        return send_file(persist_path, mimetype="text/javascript")

    # otherwise, download it and serve it
    return proxy("https://cdn.jsdelivr.net/npm/@alpinejs/persist@3/dist/cdn.min.js")


@app.route("/static/flag/<country>")
def flag(country):
    """Flag"""
    return proxy(f"https://www.rolandgarros.com/img/flags-svg/{country}.svg")


@app.route("/static/player/<int:player_id>")
def player_image(player_id):
    """Player image"""
    size = request.args.get("s", type=int) or 34  # 2.25em * 16px - border of 2px

    for player in get_rg_data("players")["players"]:
        if player["id"] == player_id:
            try:
                if player["imageUrl"]:
                    parsed_url = urlparse(player["imageUrl"])
                    query_params = parse_qs(parsed_url.query)
                    query_params["w"] = [str(size)]
                    query_params["h"] = [str(size)]
                    new_query_string = urlencode(query_params, doseq=True)
                    new_url = urlunparse(parsed_url._replace(query=new_query_string))

                    return proxy(new_url)
            except (KeyError, NotFound):
                pass
            return redirect(url_for("default_player_image", type=player["sex"]))

    raise NotFound


@app.route("/static/player/<type>")
def default_player_image(type):
    """Default player image"""
    if type in ("M", "F"):
        return proxy("https://www.rolandgarros.com/img/avatar-" + {"M": "man", "F": "woman"}[type] + ".png")

    raise NotFound


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
    return render_template("base.html", match="false")


@app.route("/match/<match_id>")
def match_page(match_id):
    """Match page"""
    return redirect("/#" + match_id)


@app.route("/api/match/<match_id>")
@check_hash
def polling_match(match_id):
    """Polling endpoint for the match pages"""
    for match_id_to_try, match in get_rg_data()["matches"].items():
        if match_id_to_try == match_id:
            return match
    raise NotFound


@app.route("/api/meta")
@check_hash
def polling_meta():
    """Polling endpoint for the metadata"""
    return get_rg_data("results/SM?meta=1")


@app.route("/api/order-of-play")
@check_hash
def polling_order_of_play():
    """Polling endpoint for the metadata"""
    return get_rg_data("order-of-play")
    # < 75 = orange


@app.route("/api/polling")
@check_hash
def polling():
    """Polling endpoint for the home page"""
    return get_rg_data()


@app.route("/results")
def results():
    """Results table"""
    return render_template("results.html")


@app.route("/api/results/<type>")
@check_hash
def polling_results(type):
    """Polling endpoint for the results table"""
    return get_rg_data(f"results/{type}")


if __name__ == "__main__":
    app.run(debug=True)
