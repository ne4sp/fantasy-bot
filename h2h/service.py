"""Расчёт H2H: результаты матчей, таблица, итоги тура."""
from __future__ import annotations

import sqlite3

from . import config, db


def name(key: str) -> str:
    return config.BY_KEY[key]["name"]


def emblem(key: str) -> str:
    return config.BY_KEY[key]["emblem"]


def tour_matches(conn: sqlite3.Connection, tour: int) -> list[dict]:
    """Результаты пар тура. Пустой список, если очков ещё нет."""
    scores = db.tour_scores(conn, tour)
    if not scores:
        return []

    matches = []
    for a, b in config.pairs_for_tour(tour):
        if a not in scores or b not in scores:
            return []
        score_a, score_b = scores[a], scores[b]
        winner = a if score_a >= score_b else b
        loser = b if winner == a else a
        matches.append({
            "home": a, "away": b,
            "score_home": score_a, "score_away": score_b,
            "winner": winner, "loser": loser,
            "winner_score": max(score_a, score_b),
            "loser_score": min(score_a, score_b),
            "draw": score_a == score_b,
        })
    return matches


def standings(conn: sqlite3.Connection, upto: int | None = None) -> list[dict]:
    """Общий зачёт H2H; upto — считать только туры по номер N включительно."""
    stats = {p["key"]: {"key": p["key"], "w": 0, "d": 0, "l": 0, "points": 0, "score": 0}
             for p in config.PLAYERS}

    tours = db.finished_tours(conn)
    if upto is not None:
        tours = [tour for tour in tours if tour <= upto]

    for tour in tours:
        for match in tour_matches(conn, tour):
            home, away = match["home"], match["away"]
            stats[home]["score"] += match["score_home"]
            stats[away]["score"] += match["score_away"]
            if match["draw"]:
                stats[home]["d"] += 1
                stats[away]["d"] += 1
                stats[home]["points"] += config.DRAW_POINTS
                stats[away]["points"] += config.DRAW_POINTS
            else:
                winner, loser = match["winner"], match["loser"]
                stats[winner]["w"] += 1
                stats[winner]["points"] += config.WIN_POINTS
                stats[loser]["l"] += 1

    return sorted(stats.values(), key=lambda s: (-s["points"], -s["score"]))


def leader(conn: sqlite3.Connection, upto: int | None = None) -> str | None:
    table = standings(conn, upto)
    return table[0]["key"] if table else None


def table_rows(conn: sqlite3.Connection, upto: int | None = None) -> list[tuple[str, int]]:
    """Общий зачёт в виде строк для карточки: (имя, очки H2H)."""
    return [(name(row["key"]), row["points"]) for row in standings(conn, upto)]
