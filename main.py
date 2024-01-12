import asyncio
import logging

from translitua import translit as tl

from parse import start_parsing


# Configure the root logger to print messages to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == '__main__':
    asyncio.run(start_parsing())