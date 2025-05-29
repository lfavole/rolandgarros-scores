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
function format_first_name(player) {
    return player.firstName.match(/^\w|(?<=\s)\w|(?<=-)\w|'\w/g)?.join("") + ".";
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
    return +date ? new Intl.DateTimeFormat("fr", {dateStyle: "short", timeStyle: "medium"}).format(date) : "";
}
function get_last(list) {
    return list[list.length - 1];
}
function won_last_set(sets, oppositeSets) {
    return get_last(sets)?.winner || (
        sets[sets.length - 2]?.winner
        && get_last(sets)?.score == 0
        && get_last(oppositeSets)?.score == 0
    );
}
function get_match_status(matchData, teamA, teamB, setsNumber) {
    // The match is over
    if(teamA.winner || teamB.winner) return "";

    // Access properties to trigger Alpine.js reactivity
    teamA.points, teamB.points, get_last(teamA.sets)?.score, get_last(teamB.sets)?.score;
    for(var [team, oppositeTeam] of [[teamA, teamB], [teamB, teamA]]) {
        var status = "";
        var firstStatus = "";
        var count = 0;
        // Team B scores `count` points and team A scores 1 point
        // Count how many times we get the same status
        while(true) {
            var team2 = structuredClone(Alpine.raw(team));
            var oppositeTeam2 = structuredClone(Alpine.raw(oppositeTeam));
            for(var i = 0; i < count; i++) {
                score_point(oppositeTeam2, team2, setsNumber);
                if(oppositeTeam2.winner) break;
            }
            if(oppositeTeam2.winner) break;
            score_point(team2, oppositeTeam2, setsNumber);
            status = "";
            if(team2.winner)
                status = "Balle de " + (matchData.roundLabel == "Finale" ? "titre" : "match");
            else if(won_last_set(team2.sets, oppositeTeam2.sets) && team2.points == "0" && oppositeTeam2.points == "0")
                status = "Balle de set";
            else if(!team.hasService && team2.points == "0")  // scored a game without serving
                status = "Balle de break";

            // If there is no status, stop here
            if(!status) break;
            // Store the first status
            firstStatus ||= status;
            // If the status has changed, stop here
            // (this will never be true during the first iteration)
            if(status != firstStatus) break;
            count++;
            // The maximal number is 10 for the super tie-break
            if(count > 10) throw new Error(`Impossible state: more than 10 '${firstStatus}'`);
        }
        // Return the number of times the status occurred
        if(firstStatus) {
            if(count == 1) return firstStatus;
            return firstStatus.replace(/Balle/, count + " balles");
        }
    }

    var lastSetA = get_last(teamA.sets);
    var lastSetB = get_last(teamB.sets);
    if(lastSetA?.score == 6 && lastSetB?.score == 6)
        return "Jeu décisif - Set n°" + team.sets.length;
    if(teamA.points == "40" && teamB.points == "40")
        return "Égalité";

    if(teamA.points == "0" && teamB.points == "0") {
        for(var [team, oppositeTeam] of [[teamA, teamB], [teamB, teamA]]) {
            if(!team.hasService) continue;
            var team2 = structuredClone(Alpine.raw(team));
            var oppositeTeam2 = structuredClone(Alpine.raw(oppositeTeam));
            for(var i = 0; i < 4; i++)
                score_point(team2, oppositeTeam2, setsNumber);
            var serve = teamA.players.length > 1 ? "Servent" : "Sert";
            if(team2.winner) return serve + " pour le " + (matchData.roundLabel == "Finale" ? "titre" : "match");
            if(won_last_set(team2.sets, oppositeTeam2.sets) && team2.points == "0" && oppositeTeam2.points == "0") return serve + " pour le set";
        }
    }
    return "";
}
function score_point(teamA, teamB, setsNumber) {
    // The match is over
    if(teamA.winner || teamB.winner) return;

    // This means that the game doesn't have started
    // But Roland-Garros should still provide us a 0-0 set
    if(!teamA?.sets?.length || !teamB?.sets?.length) return;

    // We stop as soon as the scoreboard is completely updated
    // (e.g. not if you win a point -> game -> set -> match)

    // If there are no sets in progress, create some empty sets
    if(!get_last(teamA.sets).inProgress && !get_last(teamB.sets).inProgress) {
        teamA.sets.push({score: 0, tieBreak: null, winner: false, inProgress: true, isMatchTieBreak: null});
        teamB.sets.push({score: 0, tieBreak: null, winner: false, inProgress: true, isMatchTieBreak: null});
    }

    var lastSetA = get_last(teamA.sets);
    var lastSetB = get_last(teamB.sets);

    // Let's win a point
    if(lastSetA.score == 6 && lastSetB.score == 6) {  // tie-break
        var superTieBreak = teamA.sets.length == 2 * setsNumber - 1; // 3rd or 5th set
        teamA.points++;
        if(teamA.points < (superTieBreak ? 10 : 7) || teamA.points - teamB.points < 2) {
            // Swap the services after 1, 3, 5... total points
            if((+teamA.points + +teamB.points) % 2 == 1) {
                teamA.hasService = !teamA.hasService;
                teamB.hasService = !teamB.hasService;
            }
            return;
        }
        // fall through (we won the game)
    } else {
        var addPoint = {
            "0": "15",
            "15": "30",
            "30": "40",
        };
        if(addPoint[teamA.points]) {
            if(teamB.points == "A")
                throw new Error(`Impossible state: team A has ${teamA.points == "A" ? "advantage" : teamA.points + " points"} whereas team B has advantage`);
            teamA.points = addPoint[teamA.points];
            return;
        }
        if(teamA.points == "40") {
            // equality
            if(teamB.points == "A") {
                teamB.points = "40";
                return;
            }
            // advantage for team A
            if(teamB.points == "40") {
                teamA.points = "A";
                return;
            }
            // fall through (we won a game)
        }
        if(teamA.points == "A") {
            if(teamB.points != "40")
                throw new Error(`Impossible state: team A has advantage whereas team B ${teamB.points == "A" ? "also has advantage" : "has " + teamB.points + " points"}`);
            // fall through (we won a game)
        }
    }

    // At this point we won a game
    teamA.points = "0";
    teamB.points = "0";
    lastSetA.score++;

    // The player that was already serving begins the tie-break
    // Otherwise the other player serves
    if(!(lastSetA.score == 6 && lastSetB.score == 6)) {
        teamA.hasService = !teamA.hasService;
        teamB.hasService = !teamB.hasService;
    }

    // You must have at least 6 games to win a set
    if(lastSetA.score < 6) return;
    // with a 2 games offset (or a tie-break, 7-6)
    if(lastSetA.score - lastSetB.score < 2 && !(lastSetA.score == 7 && lastSetB.score == 6)) return;

    // At this point we won a set
    lastSetA.winner = true;
    lastSetB.winner = false;
    lastSetA.inProgress = false;
    lastSetB.inProgress = false;

    // Let's win the match
    var setsWonA = 0;
    var setsWonB = 0;
    for(var i = 0; i < teamA.sets.length; i++)
        if(teamA.sets[i].winner) setsWonA++;
    for(var i = 0; i < teamB.sets.length; i++)
        if(teamB.sets[i].winner) setsWonB++;

    for(var [team, setsWon] of [["A", setsWonA], ["B", setsWonB]])
        if(setsWon > setsNumber)
            throw new Error(`Impossible state: team ${team} has won ${setsWon} sets, which is more than ${setsNumber}`);

    // If we're not about to win, create the new set
    if(setsWonA < setsNumber && setsWonB < setsNumber) {
        teamA.sets.push({score: 0, tieBreak: null, winner: false, inProgress: true, isMatchTieBreak: null});
        teamB.sets.push({score: 0, tieBreak: null, winner: false, inProgress: true, isMatchTieBreak: null});
        return;
    }

    if(setsWonA == setsNumber) {
        // Congratulations! We won the match!
        teamA.winner = true;
        teamB.winner = false;
        return;
    }

    throw new Error(`Impossible state: team B has won the match, not team A (A = ${setsWonA} sets, B = ${setsWonB} sets)`);
}

window.addEventListener("DOMContentLoaded", function() {
    if("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js", {scope: "/"})
        .then(function(reg) {
            console.log(`Service worker registration succeeded. Scope is ${reg.scope}`);
        })
        .catch(function(error) {
            console.error("Service worker registration failed:", error);
        });
    }
});
