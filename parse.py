import asyncio
import logging
import random
import re
from typing import Dict, List, Tuple

import aiohttp
from bs4 import BeautifulSoup, ResultSet, Tag
from translitua import translit as tl

from environment_vars import URL_AFISHA
from tg import send_telegram


# Performances filter
DESIRED_SHOWS = ["Конотопська відьма"]

# Day of weeek filter
DAYS_OF_WEEK = None

# DAYS_OF_WEEK = [
#     "Понеділок",
#     "Вівторок",
#     "Середа",
#     "Четвер",
#     "П\'ятниця",
#     "Субота",
#     "Неділя"
# ]

# Section & rows filter
DESIRED_SECTIONS_AND_ROWS = None

# DESIRED_SECTIONS_AND_ROWS = {
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


async def request_page(url: str) -> Tuple[str, int]:
    # API request the url
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, allow_redirects=True) as response:
            return await response.text(), response.status


def get_afisha(html_content: str) -> Tag:
    # Read the html content on the page
    soup = BeautifulSoup(html_content, features="html.parser")

    # Find the table with all shows
    afisha_table = (
        soup.find('section', {'class': 'about_ordering'})
            .find('div', {'class': 'about_order_wrap'})
            .find('div', {'class': 'wrap_table'})
            .find('table')
            .find('tbody')
    )
    return afisha_table


def get_all_shows(afisha_table: Tag) -> List[Tag]:
    # Get the element of each show
    all_shows = [
        show.find('td', {'class': 'left for-info'})
        for show in afisha_table.findChildren('tr')
        if show.find('td', {'class': 'left for-info'})
    ]
    return all_shows


def filter_by_performances(all_shows: List[Tag]) -> List[Tag]:
    selected_shows = [
        show
        for show in all_shows
        if tl(show.find('a').text.strip())
        in [tl(performance) for performance in DESIRED_SHOWS]
    ]
    return selected_shows


def filter_by_day_of_week(selected_shows: List[Tag]):
    selected_shows = [
        show
        for show in selected_shows
        if any(
            tl(day.strip()) in [tl(desired_day) for desired_day in DAYS_OF_WEEK]
            for day in show.find('h4').text.split(',')
        )
    ]


def organize_shows_as_dict(selected_shows: List[Tag]) -> List[Dict[str, str]]:
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


def organize_seats_as_dict(
    available_seats: ResultSet
) -> Dict[str, List[Dict[str, str]]]:
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


def filter_by_seat_section(
    available_seats: Dict[str, List[Dict[str, str]]]
) -> Dict[str, List[Dict[str, str]]]:
    desired_seats = {}

    # Sections filter
    for seat_section, seats in available_seats.items():
        if tl(seat_section) in [tl(section) for section in DESIRED_SECTIONS_AND_ROWS]:
            desired_seats[seat_section] = seats

    # Rows filter
    for seat_section, seats in desired_seats.items():
        desired_seats[seat_section] = [
            seat
            for seat in seats
            if re.sub(r"\D", '', seat['row'])
            in DESIRED_SECTIONS_AND_ROWS[seat_section]
        ]

    # Seats filter. Check if there're two available seats together
    for section, seats in desired_seats.items():
        paired_seats = []
        previous_seat = None

        for current_seat in seats:
            if previous_seat:
                # Check if the seats are together
                previous_seat_nr = int(re.sub(r"\D", '', previous_seat['seat']))
                current_seat_nr = int(re.sub(r"\D", '', current_seat['seat']))
                pair_seats = abs(previous_seat_nr - current_seat_nr) == 1

                if previous_seat['row'] == current_seat['row'] and pair_seats:
                    if previous_seat not in paired_seats:
                        paired_seats.append(previous_seat)
                    paired_seats.append(current_seat)

            previous_seat = current_seat
        desired_seats[section] = paired_seats

    # Filter out empty arrays in keys
    desired_seats = {
        section: seats
        for section, seats in desired_seats.items()
        if seats
    }

    return desired_seats


async def start_parsing(url: str = URL_AFISHA) -> None:
    while True:
        # Request the Afisha page
        afisha_html_content, afisha_r_code = await request_page(url)

        logging.info(f"\n[{afisha_r_code}] {url}")

        if afisha_r_code == 200:
            # Find shows on Afisha
            afisha_table = get_afisha(afisha_html_content)
            shows = get_all_shows(afisha_table)

            # Select specific shows
            if DESIRED_SHOWS:
                shows = filter_by_performances(shows)

            # Filter selected shows by day of week
            if DAYS_OF_WEEK:
                shows = filter_by_day_of_week(shows)

            # Make a list of dictionaries of selected shows
            shows = organize_shows_as_dict(shows)

            # Parse each show to find available tickets
            for show in shows:
                # Request the ticket's page
                show_html_content, show_r_code = await request_page(show['url'])

                if show_r_code == 200:
                    # Find available seats
                    available_seats = get_available_seats(show_html_content)
                    # Get section, row, seat and price
                    available_seats = organize_seats_as_dict(available_seats)
                    # Filter by section and row
                    if DESIRED_SECTIONS_AND_ROWS:
                        available_seats = filter_by_seat_section(available_seats)

                    # Notify users via Telegram Bot about available tickets
                    if available_seats.values():
                        await send_telegram(show, available_seats)

                logging.info(f"\n[{show_r_code}] {show}")

                # Pause between parsing through teh list of shows
                # await asyncio.sleep(random.randint(10, 60))

            # Pause between parsing the Afisha again
            await asyncio.sleep(random.randint(5*60, 15*60))



