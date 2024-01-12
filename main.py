import aiohttp
import asyncio
import logging
import random
import re
import string
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher
from aiogram.utils.formatting import as_marked_list, Bold, Text
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bs4 import BeautifulSoup, ResultSet
from translitua import translit as tl


# Configure the root logger to print messages to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token="5328867333:AAGW9gybl3BnGSRIyFr-aUVaM0rvmIokSkk")
dp = Dispatcher(bot=bot)
# recipients = [461829837, 337254623]

url = "http://tickets.ft.org.ua/web/afisha/"

shows = ["Конотопська відьма"]
day_of_week = ["Понеділок", "Вівторок", "Середа", "Четвер", "П\'ятниця", "Субота", "Неділя"]
desired_sections_and_rows = None
# desired_sections_and_rows = {
#     'Партер': ['1', '2'],
#     'Ложа бельєтаж центральна': ['1', '2'],
#     'Балкон-Бельєтаж': ['1'],
#     'Балкон 1 ярусу': ['1'],
#     '4 Ложа Ложа Бенуар': ['1'],
#     '5 Ложа Ложа Бенуар': ['1'],
#     '6 Ложа Ложа Бенуар': ['1'],
#     '7 Ложа Ложа Бенуар': ['1'],
#     '8 Ложа Ложа Бенуар': ['1'],
#     '9 Ложа Ложа Бенуар': ['1'],
#     '5 Ложа Ложа Бельєтаж': ['1'],
#     '6 Ложа Ложа Бельєтаж': ['1'],
#     '7 Ложа Ложа Бельєтаж': ['1'],
#     '8 Ложа Ложа Бельєтаж': ['1'],
#     '9 Ложа Ложа Бельєтаж': ['1'],
#     '10 Ложа Ложа Бельєтаж': ['1']
# }


async def parser(url: str) -> str:
    # API requets the url
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, allow_redirects=True) as response:
            return await response.text(), response.status


def ticket_box(html_content: str) -> List[Dict[str, str]]:
    # Get html content on the page
    soup = BeautifulSoup(html_content, features="html.parser")

    # Find the Afisha with all shows
    shows_table = soup.find(
        'section', {'class': 'about_ordering'}).find(
            'div', {'class': 'about_order_wrap'}).find(
                'div', {'class': 'wrap_table'}).find(
                    'table').find('tbody'
                )

    # Get the details for each show (title, date&time, href)
    all_shows = [
        show.find('td', {'class': 'left for-info'}) for show in shows_table.findChildren('tr')
        if show.find('td', {'class': 'left for-info'})
    ]

    # Filter out performances
    selected_shows = [
        show for show in all_shows
        if tl(show.find('a').text.strip()) in [tl(x) for x in shows]
    ]

    # Filter out day of week
    selected_shows = [
        show for show in selected_shows
        if any(tl(day.strip()) in [tl(x) for x in day_of_week]
            for day in show.find('h4').text.split(','))
    ]

    # Organized show details
    output = []
    for show in selected_shows:
        show_details = {
            'url': show.find('a')['href'],
            'title': show.find('a').text.strip(),
            'date': show.find('h4').text.strip()
        }
        output.append(show_details)

    return output


def get_available_seats(html_content: str) -> ResultSet:
    AVALILABLE_SEAT = {
        'name': 'rect',
        'attrs': {'class': 'b tooltip-button'}
    }

    # Get all available seats
    soup = BeautifulSoup(html_content, features="html.parser")
    available_seats = soup.find_all(**AVALILABLE_SEAT)

    return available_seats


def sort_out_available_seats(available_seats: ResultSet) -> Dict[str, List[Dict[str, str]]]:
    seats_by_section = {}

    for seat in available_seats:
        seat_details = [x.strip() for x in seat['title'].split(',')]

        section = f"{seat_details[0]} {seat_details[1]}" if "Ряд" not in seat_details[1] else seat_details[0]

        # Create a key with a section name
        if section not in seats_by_section:
            seats_by_section[section] = []

        seat_item = {
            'row': seat_details[-3],
            'seat': seat_details[-2],
            'price': seat_details[-1]
        }
        seats_by_section[section].append(seat_item)

    return seats_by_section


def desired_seats(seats) -> Dict[str, List[Dict[str, str]]]:
    desired_seats = {}

    # Sections filter
    for seat_section, seats_ in seats.items():
        if tl(seat_section) in [tl(x) for x in desired_sections_and_rows]:
            desired_seats[seat_section] = seats_

    # Rows filter
    for seat_section, seats_ in desired_seats.items():
        desired_seats[seat_section] = [
            seat for seat in seats_ if re.sub(r"\D", '', seat['row']) in desired_sections_and_rows[seat_section]
        ]

    # Seats filter. Check if there're two available seats together
    for section_, seats_ in desired_seats.items():
        match_seats = []
        current_seat = None

        for x in seats_:
            if current_seat:
                current_seat_nr = int(re.sub(r"\D", '', current_seat['seat']))
                x_seat_nr = int(re.sub(r"\D", '', x['seat']))
                pair_seats = abs(current_seat_nr - x_seat_nr) == 1

                if current_seat['row'] == x['row'] and pair_seats:
                    if current_seat not in match_seats:
                        match_seats.append(current_seat)
                    match_seats.append(x)

            current_seat = x
        desired_seats[section_] = match_seats

    desired_seats = {key: value for key, value in desired_seats.items() if value}
    return desired_seats


def text_formatter(text: str, values: Dict[str, Any]) -> Dict[str, Any]:
    output = []  # Text arguments with resolved placeholders

    for part in string.Formatter().parse(text):
        # Separating text from placeholders
        literal_text, placeholder = part[:2]
        if literal_text:
            # Append plain text into the list
            output.append(literal_text)
        if placeholder:
            # Get value for the placeholder and execute if calalble
            try:
                value = values[placeholder]
            except KeyError:
                ...
            else:
                if callable(value):
                    value = value()
                output.append(value)

    return Text(*output).as_kwargs()


async def send_telegram(show, seats) -> None:
    txt = """\
Вистава: {title}
Дата: {date}

Місця:
{seats}\
"""

    seats_ = []
    for x, y in seats.items():
        seats_.append(f"{x} ({len(y)})")

    values = {
        'title': Bold(show['title']),
        'date': Bold(show['date']),
        'seats': as_marked_list(*seats_)
    }

    text = text_formatter(txt, values)
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Посилання", url=show['url']))

    for chat_id in recipients:
        await bot.send_message(
            chat_id=chat_id,
            text=text['text'],
            entities=text['entities'],
            reply_markup=keyboard.as_markup()
        )


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)

    while True:
        html_content, code = await parser(url)
        selected_shows = ticket_box(html_content)

        for show in selected_shows:
            html_content_, code = await parser(show['url'])

            available_seats = get_available_seats(html_content_)
            available_seats = sort_out_available_seats(available_seats)
            if desired_sections_and_rows:
                available_seats = desired_seats(available_seats)

            if available_seats.values():
                await send_telegram(show, available_seats)

            logging.info(f"\n[{code}] [SEATS: {len(*available_seats.values()) if available_seats else '0'}] {show}")

            await asyncio.sleep(random.randint(10, 60))  # pause between parsing seats for each show
        await asyncio.sleep(random.randint(5*60, 15*60))  # pause between afisha parsing


if __name__ == '__main__':
    asyncio.run(main())