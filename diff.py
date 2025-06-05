def _should_recurse(obj1, obj2):
    return (
        isinstance(obj1, dict) and isinstance(obj2, dict)
        or isinstance(obj1, list) and isinstance(obj2, list)
    )


def zip_longest_dict_list(*objs: dict | list, fillvalue=None):
    """
    Return the key (or index) and a tuple containing the key
    and all the values of the passed `objs`,
    returning the `fillvalue` if the value is not present.
    """
    if len(objs) == 0:
        raise ValueError("No objects to compare")

    if len({type(obj) for obj in objs}) != 1:
        raise ValueError("Can't compare objects that are not of the same type (dict/list)")

    if isinstance(objs[0], list):
        objs = [dict(enumerate(obj)) for obj in objs]  # type: ignore

    keys = []
    for obj in objs:
        keys.extend(key for key in obj.keys() if key not in keys)  # type: ignore

    for key in keys:
        yield key, tuple(obj.get(key, fillvalue) for obj in objs)  # type: ignore


def get_diff(obj1, obj2):
    """Recursively make a diff on a `list` or on a `dict`."""
    # [added_or_edited, deleted]
    # this must be a list in order to be automatically serialized to JSON by Flask
    ret = [{}, {}]

    # placeholder for no value
    NOTHING = object()  # pylint: disable=C0103

    def recursive_diff(obj1: dict, obj2: dict, diff: list[dict] | tuple[dict, dict]):
        """Make a diff on a `list` or on a `dict`. This function is called recursively."""
        for key, (item1, item2) in zip_longest_dict_list(obj1, obj2, fillvalue=NOTHING):
            if item2 is NOTHING:
                # if the item doesn't exist anymore, remove it in the list
                diff[1][key] = 1
            elif item1 is NOTHING:
                # if the item is not present, add it in the list
                diff[0][key] = item2

            elif _should_recurse(item1, item2):
                # for dicts and lists, do a recursive diff

                # create the diff dicts
                diff[0][key] = {}
                diff[1][key] = {}
                # do the diff
                recursive_diff(obj1[key], obj2[key], (diff[0][key], diff[1][key]))

                # clean up
                for diff_l in diff:
                    # diff_l is either `added_or_edited` or `deleted`
                    if diff_l[key] == {}:
                        # if the diff is empty, remove it
                        del diff_l[key]
                    else:
                        # if the diff corresponds to a list, make it a list
                        keys0 = list(diff_l[key].keys())
                        if keys0 == list(range(len(keys0))):
                            diff_l[key] = list(diff_l[key].values())

            elif item1 != item2:
                # the object is different, remove the wrong copy and edit it
                diff[1][key] = 2  # replaced
                diff[0][key] = item2

    recursive_diff(obj1, obj2, ret)
    if not ret[1]:
        if not ret[0]:
            return {}
        return {"_a": ret[0]}
    return {"_a": ret[0], "_d": ret[1]}
