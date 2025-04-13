#!/usr/bin/env python3

import asyncio
import click

from main import main as main_async
from icloud import HideMyEmail
from utils.logger import logger

@click.group()
def cli():
    """iCloud Yashirin Email Generator CLI"""
    pass

@cli.command()
@click.option("--count", default=5, help="Generatsiya qilinadigan email soni", type=int)
@click.option("--batch", default=5, help="Har bir partiyadagi email soni", type=int)
def generate(count: int, batch: int):
    """Email generatsiya qilish"""
    asyncio.run(main_async.generate_with_schedule(count, batch))

@cli.command()
@click.option("--active/--inactive", default=True, help="Faol/nofaol emaillarni ko'rsatish")
@click.option("--search", default=None, help="Qidiruv uchun kalit so'z")
@click.option("--save", is_flag=True, help="Natijalarni CSV fayliga saqlash")
def list(active: bool, search: str, save: bool):
    """Email ro'yxatini ko'rsatish"""
    asyncio.run(main_async.list_emails(active, search, save))

if __name__ == "__main__":
    cli()
