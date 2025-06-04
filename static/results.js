function getPart(round, start, total) {
    if(!total) return round;
    var ret = {};
    for(var key in round) {
        if(key == "matches") {
            var l = Object.keys(round.matches).length;
            ret.matches = Object.fromEntries(
                Object.entries(round.matches).slice(start / total * l, (start + 1) / total * l)
            );
            continue;
        }
        ret[key] = round[key];
    }
    return ret;
}

function parseDisplay(display) {
    var match = display.match(/^(\d+)(?:_(\d+)_(\d+))?$/);
    if(!match) throw new Error("Unrecognized display type: " + display);

    var startIndex = +match[1];
    var start = +match[2];
    var total = +match[3];
    return [startIndex, start, total];
}

function getDisplayedData(data, display, maxRoundsCount) {
    if(!data) return [];
    [startIndex, start, total] = parseDisplay(display);

    var ret = [];
    for(var item, i = 0; i < maxRoundsCount; i++) {
        item = getPart(data[startIndex + i], start, total);
        if(item) ret.push(item);
    }
    return ret;
}
