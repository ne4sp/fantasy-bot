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


def _round_robin(keys: list[str]) -> list[list[tuple[str, str]]]:
    """Круговой турнир (метод круга): n-1 туров по n/2 пар."""
    n = len(keys)
    arr = list(keys)
    rounds = []
    for _ in range(n - 1):
        rounds.append([(arr[i], arr[n - 1 - i]) for i in range(n // 2)])
        arr = [arr[0], arr[-1], *arr[1:-1]]
    return rounds


ROUNDS = _round_robin([p["key"] for p in PLAYERS])


def pairs_for_tour(tour: int) -> list[tuple[str, str]]:
    """Пары тура. После 5-го тура цикл повторяется."""
    return ROUNDS[(tour - 1) % len(ROUNDS)]
