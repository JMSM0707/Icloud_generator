#!/usr/bin/env python3

import asyncio
import click
from main import RichHideMyEmail

@click.group()
def cli():
    """iCloud Hide My Email Manager with Scheduled Generation"""
    pass

async def _generate(total: int, batch_size: int, delay: float):
    async with RichHideMyEmail() as hme:
        await hme.generate_with_schedule(total, batch_size, delay)

async def _list(active, search):
    async with RichHideMyEmail() as hme:
        await hme.list_emails(active=active, search=search)

@click.command()
@click.option("--total", default=5, help="Total number of emails to generate", type=int)
@click.option("--batch-size", default=5, help="Number of emails per batch", type=int)
@click.option("--delay", default=1, help="Delay between batches in hours", type=float)
def generate(total: int, batch_size: int, delay: float):
    """Generate emails in scheduled batches"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_generate(total, batch_size, delay))
    except KeyboardInterrupt:
        print("\nGeneration interrupted by user")
    finally:
        loop.close()

@click.command()
@click.option("--active/--inactive", default=True, help="Filter Active/Inactive emails")
@click.option("--search", default=None, help="Search emails by label")
def list(active, search):
    """List existing emails"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_list(active, search))
    except KeyboardInterrupt:
        print("\nListing interrupted by user")
    finally:
        loop.close()

cli.add_command(list, name="list")
cli.add_command(generate, name="generate")

if __name__ == "__main__":
    cli()