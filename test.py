import asyncio
import logging
import random
import re
from typing import Dict, List, Union

import aiohttp
from bs4 import BeautifulSoup, ResultSet
from translitua import translit as tl

from environment_vars import URL_AFISHA


from aiohttp import ClientResponse




async def request_page(url: str) -> str:
    # API request the url
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, allow_redirects=True) as response:
            return await response.text(), response.status


def get_all_shows(html_content: str) -> List[Dict[str, str]]:
    # Read the html content on the page
    soup = BeautifulSoup(html_content, features="html.parser")

    # Find the table with all shows
    shows_table = soup.find(
        'section', {'class': 'about_ordering'}
        ).find(
            'div', {'class': 'about_order_wrap'}
            ).find(
                'div', {'class': 'wrap_table'}
                ).find(
                    'table'
                    ).find(
                        'tbody'
                        )

    return shows_table


def bb(afisha_table):
    # Get the details for each show (title, date&time, href)
    all_shows = [
        show.find('td', {'class': 'left for-info'})
        for show in afisha_table.findChildren('tr')
        if show.find('td', {'class': 'left for-info'})
    ]
    for i in all_shows:
        print(type(i))


async def main():
    page, code = await request_page(URL_AFISHA)
    a = get_all_shows(page)
    b = bb(a)


asyncio.run(main())