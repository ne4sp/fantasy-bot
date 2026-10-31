"""Конфигурация H2H-лиги."""
from __future__ import annotations

# Фэнтези-сезон и приватная лига на sports.ru
SEASON_ID = "75"
LEAGUE_ID = "42767"

# 5 реальных участников + 6-й бот (среднее по лиге за тур)
PLAYERS = [
    {"key": "ivan",   "name": "DeepinиBottom",   "squad_id": "581401", "emblem": "ivan.png"},
    {"key": "kostya", "name": "WINEGREAT",       "squad_id": "581089", "emblem": "kostya.png"},
    {"key": "sasha",  "name": "Moget ne broshy", "squad_id": "582340", "emblem": "sasha.png"},
    {"key": "serega", "name": "Серёга, ты где?", "squad_id": "581933", "emblem": "serega.png"},
    {"key": "vova",   "name": "Shipibo-Conibo",  "squad_id": "574716", "emblem": "vova.png"},
    {"key": "sixth",  "name": "sixth",           "squad_id": None,     "emblem": "sixth.png"},
]
BY_KEY = {p["key"]: p for p in PLAYERS}
REAL_PLAYERS = [p["key"] for p in PLAYERS if p["squad_id"]]
AVERAGE_PLAYER = "sixth"

WIN_POINTS = 3
DRAW_POINTS = 1


# Расписание, составленное вручную (5 туров, далее цикл повторяется).
# В каждом туре каждый участник играет ровно один раз.
ROUNDS = [
    # 1 тур: Вовка–№6, Костик–Санек, Ванюша–Серега
    [("vova", "sixth"), ("kostya", "sasha"), ("ivan", "serega")],
    # 2 тур: Вовка–Санек, Серега–№6, Костик–Ванюша
    [("vova", "sasha"), ("serega", "sixth"), ("kostya", "ivan")],
    # 3 тур: Вовка–Серега, Санек–Ванюша, №6–Костик
    [("vova", "serega"), ("sasha", "ivan"), ("sixth", "kostya")],
    # 4 тур: Ванюша–Вовка, Костик–Серега, Санек–№6
    [("ivan", "vova"), ("kostya", "serega"), ("sasha", "sixth")],
    # 5 тур: Вовка–Костик, Ванюша–№6, Санек–Серега
    [("vova", "kostya"), ("ivan", "sixth"), ("sasha", "serega")],
]


def pairs_for_tour(tour: int) -> list[tuple[str, str]]:
    """Пары тура. После 5-го тура цикл повторяется."""
    return ROUNDS[(tour - 1) % len(ROUNDS)]
