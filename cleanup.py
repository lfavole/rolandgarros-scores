from copy import deepcopy
from typing import Any, Callable


YES = object()
cleanup_matches = {
    "matches": [
        {
            "excitementRate": None,
            "matchData": {
                "courtName": YES,
                "dateSchedule": YES,
                "durationInMinutes": None,
                "isNightSession": False,
                "notBefore": None,
                "roundLabel": YES,
                "startingAt": None,
                "status": YES,
                "type": YES,
                "typeLabel": YES,
            },
            "teamA": {
                "endCause": None,
                "entryStatus": None,
                "hasService": False,
                "players": [
                    {
                        "country": YES,
                        "firstName": YES,
                        "id": YES,
                        "lastName": YES,
                    }
                ],
                "points": YES,
                "seed": None,
                "sets": [
                    {
                        "inProgress": False,
                        "score": YES,
                        "tieBreak": False,
                        "winner": False,
                    }
                ],
                "winner": False,
            },
        }
    ]
}
cleanup_matches["matches"][0]["teamB"] = cleanup_matches["matches"][0]["teamA"]

cleanup_results = [
    {
        "roundLabel": YES,
        "roundNumber": YES,
        "matches": cleanup_matches["matches"],
    }
]

cleanup_meta = {
    "types": [{"code": YES, "label": YES}],
    "eventYears": YES,
}

fixups: dict[str, tuple[type | tuple[type, ...], Callable[[Any], Any]]] = {
    "excitementRate": ((int, type(None)), lambda er: round((er or {}).get("pre_match_percent", 0)) or None),
    "matches": (dict, lambda matches: {match["id"]: deepcopy(match) for match in matches}),
    "types": (dict, lambda matches: {match["code"]: match["label"] for match in matches}),
}


def recursive_cleanup(data, schema):
    if isinstance(data, list):
        for item in data:
            recursive_cleanup(item, schema[0])
        return data

    if isinstance(data, dict):
        if isinstance(schema, list):
            for key in list(data):
                recursive_cleanup(data[key], schema[0])
            return data

        for key in list(data):
            if key not in schema:
                del data[key]
            elif key in schema:
                if key in fixups and not isinstance(data[key], fixups[key][0]):
                    data[key] = fixups[key][1](data[key])
                if isinstance(schema[key], (list, dict)):
                    recursive_cleanup(data[key], schema[key])
                elif schema[key] == data[key]:
                    del data[key]

    return data


def recursive_fixup(data):
    if isinstance(data, list):
        for item in data:
            recursive_fixup(item)
        return data

    if isinstance(data, dict):
        for key in list(data):
            if key in fixups and not isinstance(data[key], fixups[key][0]):
                data[key] = fixups[key][1](data[key])
            else:
                recursive_fixup(data[key])

    return data


def cleanup_rg_data(endpoint, rg_data, style):
    """
    Clean up the `rg_data` returned by the Roland-Garros server
    by removing all the unnecessary information
    and make it suitable for the given `style`.
    """
    cleanup_dict = None
    if endpoint == "polling":
        cleanup_dict = cleanup_matches
    elif "?meta=1" in endpoint:
        cleanup_dict = cleanup_meta
    elif endpoint.startswith("results/"):
        rg_data = rg_data["tournamentEvent"]["roundResults"] or []
        cleanup_dict = cleanup_results

    rg_data = deepcopy(rg_data)

    if style == "all" or cleanup_dict is None:
        recursive_fixup(rg_data)
        return rg_data

    recursive_cleanup(rg_data, cleanup_dict)
    return rg_data
