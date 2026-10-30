import asyncio, httpx
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

# Время матчей в API РПЛ всегда в UTC, а вся логика бота — в московском времени.
MOSCOW = ZoneInfo("Europe/Moscow")


def parse_api_date(date_str: str) -> datetime:
    """Разбирает дату из API РПЛ ("2026-10-31UTC17:30:00") в aware-время по Москве."""
    cleaned = date_str.replace("UTC", " ").strip()
    return (
        datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .astimezone(MOSCOW)
    )


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


GROUP_ID = -549417257
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
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())