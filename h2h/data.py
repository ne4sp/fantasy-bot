"""Загрузка данных фэнтези с GraphQL sports.ru."""
from __future__ import annotations

import httpx

from . import config, db

URL = "https://www.sports.ru/gql/graphql/"
HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


async def fetch_tours(client: httpx.AsyncClient) -> list[dict]:
    query = (
        "{ fantasyQueries { season(input: {seasonID: \"%s\"}) {"
        " tours { id name status finishedAt } } } }" % config.SEASON_ID
    )
    resp = await client.post(URL, json={"query": query}, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["data"]["fantasyQueries"]["season"]["tours"]


async def fetch_tour_scores(client: httpx.AsyncClient, tour_id: str) -> dict[str, int]:
    """Очки всех реальных участников за конкретный тур (один запрос)."""
    parts = []
    for player in config.PLAYERS:
        squad_id = player["squad_id"]
        if not squad_id:
            continue
        parts.append(
            f'{player["key"]}: squadTourInfo(input: {{squadID: "{squad_id}", '
            f'tourID: "{tour_id}"}}) {{ scoreInfo(leagueID: "{config.LEAGUE_ID}") {{ score }} }}'
        )
    query = "{ fantasyQueries { " + " ".join(parts) + " } }"
    resp = await client.post(URL, json={"query": query}, headers=HEADERS)
    resp.raise_for_status()
    node = resp.json()["data"]["fantasyQueries"]

    scores: dict[str, int] = {}
    for player in config.PLAYERS:
        if not player["squad_id"]:
            continue
        info = (node.get(player["key"]) or {}).get("scoreInfo") or {}
        if info.get("score") is not None:
            scores[player["key"]] = int(info["score"])
    return scores


async def sync(conn) -> None:
    """Подтягивает туры и очки завершённых туров, которых ещё нет в БД."""
    async with httpx.AsyncClient(timeout=30) as client:
        for tour in await fetch_tours(client):
            number = int(tour["name"].split()[0])
            db.upsert_tour(conn, number, tour["id"], tour["status"], tour.get("finishedAt"))

            if tour["status"] != "FINISHED" or db.tour_scores(conn, number):
                continue

            scores = await fetch_tour_scores(client, tour["id"])
            if len(scores) == len(config.REAL_PLAYERS):
                scores[config.AVERAGE_PLAYER] = round(sum(scores.values()) / len(scores))
                db.upsert_scores(conn, number, scores)
        conn.commit()
