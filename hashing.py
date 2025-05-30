from functools import wraps
from hashlib import sha1
from typing import Any

from flask import Response, current_app, request

from diff import get_diff  # type: ignore


# the data depending on the hash
# this is paradoxal, but only the hash is hashable and
# can be used as a dict key
hashes: dict[str, Any] = {}


def get_hash(obj):
    """Return the hash for a given `obj`."""
    # check if the hash is known
    for hash, test_obj in hashes.items():
        if test_obj == obj:
            return hash

    # clean up the hashes dict if there are too much
    # keep only 50 hashes every 100 hashes
    if len(hashes) > 100:
        for key in list(hashes.keys())[:50]:
            del hashes[key]

    # compute the hash and save it in the dict
    hash = sha1(current_app.json.dumps(obj).encode("utf-8")).hexdigest()[0:8]
    hashes[hash] = obj
    return hash


def check_hash(f):
    """
    A decorator that returns:
    * an empty response if the local and server data have the same hash,
    * a JSON diff if a known hash (still in the cache) is specified
    * a complete JSON data dict otherwise
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        ret = f(*args, **kwargs)
        expected_hash = request.args.get("hash")

        if get_hash(ret) == expected_hash:
            return Response()

        if expected_hash and expected_hash in hashes:
            return get_diff(hashes[expected_hash], ret)

        return ret

    return decorator
