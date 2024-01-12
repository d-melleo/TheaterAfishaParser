import string
from typing import Any, Dict

from aiogram import Bot, Dispatcher
from aiogram.utils.formatting import as_marked_list, Bold, Text
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .environment_vars import BOT_TOKEN, RECIPIENTS


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)


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


def message_content(show, seats) -> Dict[str, Any]:
    # Template
    txt = """\
Вистава: {title}
Дата: {date}

Місця:
{seats}\
"""

    # Number of avaialable seats in each section
    seats_ = []
    for section, seat in seats.items():
        seats_.append(f"{section} ({len(seat)})")

    # Formatting vaules
    values = {
        'title': Bold(show['title']),
        'date': Bold(show['date']),
        'seats': as_marked_list(*seats_)
    }

    # Formatted text
    msg_content: Dict[str, Any] = text_formatter(txt, values)

    # Link button for the show
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Посилання", url=show['url']))
    msg_content['reply_markup'] = keyboard

    return msg_content


async def send_telegram(show, seats) -> None:
    for chat_id in RECIPIENTS:
        await bot.send_message(
            chat_id=chat_id,
            **message_content(show, seats)
        )