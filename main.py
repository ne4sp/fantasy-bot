import asyncio, httpx
import io
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InputMediaPhoto
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from h2h import config as h2h_config
from h2h import data as h2h_data
from h2h import db as h2h_db
from h2h import render as h2h_render
from h2h import service as h2h_service

load_dotenv()

# В API РПЛ время уже московское, хотя в строке стоит суффикс "UTC"
# (проверено: 2026-10-31UTC15:15:00 — это 15:15 МСК, а не 18:15).
MOSCOW = ZoneInfo("Europe/Moscow")


def parse_api_date(date_str: str) -> datetime:
    """Разбирает дату из API РПЛ ("2026-10-31UTC15:15:00") как время по Москве."""
    cleaned = date_str.replace("UTC", " ").strip()
    return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW)


def club_name(club_id: int) -> str:
    club = CLUBS.get(club_id)
    return club["name"] if club else f"Клуб {club_id}"


WEEKDAYS = {
    0: "Понедельник", 1: "Вторник", 2: "Среда",
    3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
}

MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


GROUP_ID = int(os.getenv("GROUP_ID", "-549417257"))
CLUBS = {
    1: {"name": "Спартак-Москва", "nameShort": "СПА"},
    2: {"name": "ПФК ЦСКА", "nameShort": "ЦСКА"},
    3: {"name": "Зенит", "nameShort": "ЗЕН"},
    4: {"name": "Рубин", "nameShort": "РУБ"},
    5: {"name": "Локомотив", "nameShort": "ЛОК"},
    6: {"name": "Шинник", "nameShort": "ШИН"},
    7: {"name": "Динамо-Москва", "nameShort": "ДИН"},
    8: {"name": "Сатурн", "nameShort": "САТ"},
    9: {"name": "Торпедо Москва", "nameShort": "ТОР"},
    10: {"name": "Крылья Советов", "nameShort": "КРС"},
    11: {"name": "Ростов", "nameShort": "РОС"},
    12: {"name": "Ротор", "nameShort": "РОТ"},
    13: {"name": "Алания", "nameShort": "АЛВ"},
    14: {"name": "Москва", "nameShort": "МСК"},
    15: {"name": "Амкар", "nameShort": "АМК"},
    16: {"name": "Кубань", "nameShort": "КУБ"},
    21: {"name": "Терек", "nameShort": "ТРК"},
    41: {"name": "Томь", "nameShort": "ТОМ"},
    82: {"name": "Уралан", "nameShort": "УРН"},
    83: {"name": "Черноморец", "nameShort": "ЧЕР"},
    86: {"name": "Химки", "nameShort": "ХИМ"},
    87: {"name": "Арсенал", "nameShort": "АРС"},
    125: {"name": "Динамо Махачкала", "nameShort": "ДМХ"},
    127: {"name": "Сокол", "nameShort": "СКЛ"},
    131: {"name": "СКА-Хабаровск", "nameShort": "СКА"},
    147: {"name": "Спартак-Нальчик", "nameShort": "НАЛ"},
    150: {"name": "Урал", "nameShort": "УРЛ"},
    153: {"name": "Луч", "nameShort": "ЛУЧ"},
    264: {"name": "Факел", "nameShort": "ФКЛ"},
    266: {"name": "Мордовия", "nameShort": "МРД"},
    268: {"name": "Анжи", "nameShort": "АНЖ"},
    285: {"name": "Сибирь", "nameShort": "СИБ"},
    444: {"name": "Балтика", "nameShort": "БАЛ"},
    484: {"name": "Волга НН", "nameShort": "ВНН"},
    504: {"name": "Оренбург", "nameShort": "ОРЕ"},
    525: {"name": "Сочи", "nameShort": "СОЧ"},
    584: {"name": "Краснодар", "nameShort": "КРА"},
    637: {"name": "Енисей", "nameShort": "ЕНИ"},
    674: {"name": "Уфа", "nameShort": "УФА"},
    693: {"name": "Тосно", "nameShort": "ТОС"},
    696: {"name": "Тамбов", "nameShort": "ТАМ"},
    702: {"name": "Ахмат", "nameShort": "АХМ"},
    704: {"name": "Пари НН", "nameShort": "ПНН"},
    807: {"name": "Акрон", "nameShort": "АКР"},
    808: {"name": "Родина", "nameShort": "РОД"}
}

API_TOKEN = os.getenv('MAIN_KEY')
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
# Явно задаём таймзону, а не полагаемся на TZ/tzset (в slim-образе нет /usr/share/zoneinfo).
scheduler = AsyncIOScheduler(timezone=MOSCOW)

H2H_DB = os.getenv("H2H_DB", "h2h.db")
h2h_conn = h2h_db.connect(H2H_DB)
H2H_ANNOUNCE = os.getenv("H2H_ANNOUNCE", "1") != "0"


async def get_deadline_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://premierliga.ru/",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            init_res = await client.get("https://api.premierliga.ru/api/init")
            init_data = init_res.json()

            t_id = init_data.get("currentTournament")
            s_id = init_data.get("currentStage")

            matches_res = await client.post(
                "https://api.premierliga.ru/api/getMatches",
                json={"tournament": t_id}
            )

            matches_data = matches_res.json()
            target_matches = [
                m for m in matches_data
                if m.get("stage") == s_id
            ]

            if not target_matches:
                return None

            all_matches = target_matches[0]['matches']

            earliest_match = min(all_matches, key=lambda x: parse_api_date(x['date']))

            return earliest_match
        except Exception as e:
            print(f"Ошибка: {e}")
            return None


@dp.message(Command("dl"))
async def cmd_dl(message: types.Message):
    dt_f = await get_deadline_data()

    if not dt_f:
        await message.answer("❌ Не удалось найти ближайшие матчи. ❌")
        return

    dt = parse_api_date(dt_f['date'])

    if dt < datetime.now(MOSCOW):
        # Если матчей в этом туре больше нет (все в прошлом)
        response = (
            "🏁 <b>Дедлайн текущего тура уже прошёл!</b> 🏁\n"
            "┕ Ждём обновления данных от РПЛ для следующего тура.\n"
            "┕ <a href='https://www.sports.ru/fantasy/football/russia/'><b>Твоя fantasy команда</b></a>"
        )
        return await message.answer(response, parse_mode='HTML')

    dt_h = club_name(dt_f['clubH'])
    dt_a = club_name(dt_f['clubA'])

    weekday = WEEKDAYS[dt.weekday()]

    day_str = f"{dt.day}-го {MONTHS[dt.month]}"
    time_str = dt.strftime("%H:%M")

    response = (
        f"<b>{dt_h} — {dt_a}</b>\n"
        f"┕ <code> {weekday} ┃ {day_str} ┃ {time_str}</code>\n"
        f"┕ <a href='https://www.sports.ru/fantasy/football/russia/'>  <b>Твоя fantasy команда </b> </a>"
    )

    await message.answer(response, parse_mode="HTML")

@dp.message(Command("table"))
async def get_league_table(message: types.Message):
    url = "https://www.sports.ru/gql/graphql/"

    # Заголовки (базовые)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # Твой запрос (чуть подправил pageSize до 10)
    payload = {
            "query": """
            {
              id_225191701: fantasyQueries {
                rating {
                  squads(input: {
                    entityID: "75",
                    entityType: SEASON,
                    sortOrder: DESC,
                    leagueID: 42767,
                    pageSize: 10,
                    pageNum: 1
                  }) {
                    list {
                      squad { name }
                      scoreInfo { place score scoreForLastTour }
                    }
                  }
                }
              }
            }
            """
        }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
            items = data['data']['id_225191701']['rating']['squads']['list']

            lines = ["🏆 <b>Бланш-на-Дону</b> 🍺\n"]

            for item in items:
                info = item['scoreInfo']
                place = info['place']
                name = item['squad']['name']
                total = info['score']
                last = info['scoreForLastTour']

                # Присваиваем медаль или номер
                if place == 1:
                    prefix = "🥇"
                elif place == 2:
                    prefix = "🥈"
                elif place == 3:
                    prefix = "🥉"
                else:
                    prefix = f"  {place}."

                # Красивая строка: Всего | +Тур
                lines.append(f"{prefix} <code>{name}</code> — {total} | +{last}")

            response = "\n".join(lines)
            await message.answer(response, parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Ошибка загрузки данных: {e}")


def _emblem_path(key: str) -> str:
    return os.path.join(h2h_render.EMBLEMS, h2h_service.emblem(key))


def _png(img) -> bytes:
    """Карточка уходит в Telegram как фото, поэтому JPEG (PNG ~1.4 МБ)."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


def _match_images(tour: int) -> list[bytes]:
    images = []
    for m in h2h_service.tour_matches(h2h_conn, tour):
        img = h2h_render.render_match(
            h2h_service.name(m["winner"]),
            h2h_service.name(m["loser"]),
            m["winner_score"],
            m["loser_score"],
            _emblem_path(m["winner"]),
        )
        images.append(_png(img))
    return images


def _overall_image(tour: int) -> bytes:
    """Общий зачёт H2H после тура N — картинкой, без текстовой таблицы."""
    lead = h2h_service.leader(h2h_conn, upto=tour)
    img = h2h_render.render_overall(
        h2h_service.table_rows(h2h_conn, upto=tour),
        _emblem_path(lead) if lead else None,
    )
    return _png(img)


async def _send_photos(chat_id: int, images: list[bytes], caption: str | None = None) -> None:
    media = [
        InputMediaPhoto(
            media=BufferedInputFile(data, filename=f"h2h_{i}.jpg"),
            caption=caption if i == 0 else None,
            parse_mode="HTML" if i == 0 and caption else None,
        )
        for i, data in enumerate(images)
    ]
    await bot.send_media_group(chat_id, media)


async def _send_tour_results(chat_id: int, tour: int) -> None:
    images = _match_images(tour)
    if images:
        await _send_photos(chat_id, images)
    await bot.send_photo(
        chat_id,
        BufferedInputFile(_overall_image(tour), filename=f"overall_{tour}.jpg"),
        caption=f"🏆 <b>Общий зачёт H2H после {tour} тура</b>",
        parse_mode="HTML",
    )


@dp.message(Command("h2h"))
async def cmd_h2h(message: types.Message):
    await h2h_data.sync(h2h_conn)

    parts = (message.text or "").split()
    tour = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    if tour is None:
        finished = h2h_db.finished_tours(h2h_conn)
        if not finished:
            await message.answer("Пока нет завершённых туров.")
            return
        tour = finished[-1]

    status = h2h_db.tour_status(h2h_conn, tour)
    if status is None:
        await message.answer(f"Тур {tour} не найден.")
        return

    if status != "FINISHED" or not h2h_db.tour_scores(h2h_conn, tour):
        pairs = "\n".join(
            f"• {h2h_service.name(a)} — {h2h_service.name(b)}"
            for a, b in h2h_config.pairs_for_tour(tour)
        )
        await message.answer(f"📅 <b>Тур {tour}</b> — расписание\n{pairs}", parse_mode="HTML")
        return

    await _send_tour_results(message.chat.id, tour)


async def announce_h2h_results():
    await h2h_data.sync(h2h_conn)

    # При первом запуске не спамим всеми прошедшими турами.
    if not h2h_db.get_meta(h2h_conn, "announced_init"):
        for tour in h2h_db.finished_tours(h2h_conn):
            h2h_db.set_meta(h2h_conn, f"announced:{tour}", "1")
        h2h_db.set_meta(h2h_conn, "announced_init", "1")
        h2h_conn.commit()
        return

    now = datetime.now(timezone.utc)
    for tour in h2h_db.finished_tours(h2h_conn):
        if h2h_db.get_meta(h2h_conn, f"announced:{tour}"):
            continue
        finished_at = h2h_db.tour_finished_at(h2h_conn, tour)
        if not finished_at or now < finished_at + timedelta(hours=2):
            continue
        if not h2h_db.tour_scores(h2h_conn, tour):
            continue

        await _send_tour_results(GROUP_ID, tour)
        h2h_db.set_meta(h2h_conn, f"announced:{tour}", "1")
        h2h_conn.commit()


async def send_reminder(text):
    try:
        await bot.send_message(GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки: {e}")


async def schedule_deadlines():
    """Планирует напоминания для ближайшего матча текущего тура.

    Вызывается при старте и периодически (см. main), поэтому должна быть
    идемпотентной: повторный вызов не создаёт дублей, а уже прошедшие
    напоминания пропускает.
    """
    dt_f = await get_deadline_data()
    if not dt_f:
        return

    dt = parse_api_date(dt_f['date'])
    dt_h = club_name(dt_f['clubH'])
    dt_a = club_name(dt_f['clubA'])
    match_id = dt_f.get('id', f"{dt_f['clubH']}_{dt_f['clubA']}")

    day_str = f"{dt.day}-е {MONTHS[dt.month]}"
    time_str = dt.strftime("%H:%M")

    now = datetime.now(MOSCOW)

    morning_time = dt.replace(hour=8, minute=10, second=0, microsecond=0)
    if now < morning_time < dt:
        text = (
            f"🔔 Сегодня дедлайн! 🔔\n"
            f"<b>{dt_h} — {dt_a}</b>\n"
            f"┕ <code> {day_str} ┃ {time_str}</code>\n"
            f"┕ <a href='https://www.sports.ru/fantasy/football/russia/'>  <b>Твоя fantasy команда</b></a>"
        )
        scheduler.add_job(
            send_reminder, 'date', run_date=morning_time, args=[text],
            id=f"morning_{match_id}", replace_existing=True,
        )

    hour_before = dt - timedelta(hours=1)
    if hour_before > now:
        text_h = (
            f"⚠️ До дедлайна остался 1 час! ⚠️\n"
            f"<b>{dt_h} — {dt_a}</b>\n"
            f"┕ <code> {day_str} ┃ {time_str}</code>\n"
            f"┕ <a href='https://www.sports.ru/fantasy/football/russia/'>  <b>Твоя fantasy команда</b></a>"
        )
        scheduler.add_job(
            send_reminder, 'date', run_date=hour_before, args=[text_h],
            id=f"hour_before_{match_id}", replace_existing=True,
        )


async def main():
    scheduler.start()
    await schedule_deadlines()
    # Перечитываем тур каждые 6 часов: иначе после смены тура напоминания
    # для следующего матча никогда не запланируются (процесс живёт неделями).
    scheduler.add_job(
        schedule_deadlines, 'cron', hour="*/6", minute=5,
        id="refresh_deadlines", replace_existing=True, max_instances=1,
    )
    # H2H: проверяем, не закончился ли тур (+2 часа) и не пора ли постить итоги.
    # H2H_ANNOUNCE=0 отключает автопостинг (нужно для дебаг-бота, чтобы не дублировать).
    if H2H_ANNOUNCE:
        scheduler.add_job(
            announce_h2h_results, 'interval', minutes=10,
            id="h2h_results", replace_existing=True, max_instances=1,
        )
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
