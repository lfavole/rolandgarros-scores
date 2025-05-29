from copy import deepcopy


YES = object()
keys_to_keep = {
    "matches": [
        {
            "id": YES,
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
                        "country": lambda style: style == "website",
                        "firstName": YES,
                        "id": lambda style: style == "website",
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
keys_to_keep["matches"][0]["teamB"] = keys_to_keep["matches"][0]["teamA"]


def cleanup_rg_data(rg_data, style):
    """
    Clean up the `rg_data` returned by the Roland-Garros server
    by removing all the unnecessary information
    and make it suitable for the given `style`.
    """
    if style is None:
        return rg_data

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
                elif schema[key] == data[key]:
                    del data[key]

        return data

    recursive_cleanup(rg_data, keys_to_keep)
    return rg_data
