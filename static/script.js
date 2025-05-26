var STATUSES_LABELS = {
    "ABANDON": "abandon",
    "CANCELED": "reporté",
    "DISQUALIFIED": "disqualifié",
    "FINISHED": "terminé",
    "FORFAIT": "forfait",
    "IN_PROGRESS": "en cours",
    "INTERRUPTED": "interrompu",
    "NOT_STARTED": "à venir",
    "TO_FINISH": "à finir",
};
var STATUSES_COLORS = {
    "IN_PROGRESS": "green",
    "TO_FINISH": "green",
    "FINISHED": "blue",
    "NOT_STARTED": "blue",
    // all the other statuses are red
};
var STATUSES_DISPLAY = {
    "NOT_STARTED": "upcoming",
    "CANCELED": "upcoming",
    "TO_FINISH": "upcoming",
    "IN_PROGRESS": "live",
    "INTERRUPTED": "live",
    // all the other statuses are "finished"
};
var ENDCAUSES_LABELS = {
    "ab.": "Abandon",
    "d.": "Disqualifié",
    "w/o.": "Forfait",
};
function format_rg_date(date) {
    return date.replace(/^(\d\d\d\d)(\d\d)(\d\d)$/, "$3/$2/$1");
}
function format_duration(duration, use_h) {
    return Math.floor(duration / 60) + (use_h ? "h" : ":") + (duration % 60 < 10 ? "0": "") + duration % 60;
}
function format_small_duration(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);

    const parts = [];
    if (hours > 0) {
        parts.push(hours + " heure" + (hours >= 2 ? "s" : ""));
    }
    if (parts && minutes > 0) {
        parts.push(minutes + " minute" + (minutes >= 2 ? "s" : ""));
    }
    if (parts && seconds > 0 || parts.length === 0) {
        parts.push(seconds + " seconde" + (seconds >= 2 ? "s" : ""));
    }

    return parts.join(" ");
}
function format_last_name(player) {
    return player.lastName.toLowerCase().replace(/^\w|\s\w|-\w|'\w/g, (char) => char.toUpperCase());
}
function winner_class(obj, match) {
    var ret = obj.winner ? "won" : "lost";  // early evaluation for Alpine.js
    if(obj.inProgress) return "";
    var status = (match || obj).matchData && (match || obj).matchData.status;
    if(status && status != "FINISHED") return "";
    return ret;
}
function format_date(date) {
    return new Intl.DateTimeFormat("fr", {dateStyle: "short", timeStyle: "medium"}).format(date);
}
