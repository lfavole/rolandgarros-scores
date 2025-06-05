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
            # re-set the key to prevent it from being cleaned up
            del hashes[hash]
            hashes[hash] = test_obj
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

        # Cache hashes
        _ = get_hash(ret)
        if "polling" in request.url:
            for key in ret:
                _ = get_hash(ret[key])

        if expected_hash and expected_hash in hashes:
            client_data = hashes[expected_hash]
        else:
            client_data = {}
            for arg, value in request.args.items():
                if not arg.startswith("hash."):
                    continue
                key = arg[5:]
                # The client has something, but we don't know what
                client_data[key] = object()
                # If the key is not present, don't bother calculating the hash
                if key not in ret:
                    continue
                if value in hashes:
                    # The client has something that we know (i.e. that we had)
                    client_data[key] = hashes[value]

        if not client_data:
            return ret

        if request.args.get("only"):
            ret = {key: value for key, value in ret.items() if key in client_data}

        return get_diff(client_data, ret) or Response()

    return decorator
