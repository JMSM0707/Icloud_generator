#!/usr/bin/env python3

import asyncio
import click
import logging
import pytz
from datetime import datetime
from rich.progress import Progress, ProgressColumn
from main import RichHideMyEmail

# Jurnal yozish sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hide_my_email.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MoscowTimeColumn(ProgressColumn):
    """Hozirgi Moskva vaqtini ko'rsatish uchun maxsus ustun"""
    def __init__(self):
        super().__init__()
        self.tz = pytz.timezone('Europe/Moscow')
    
    def render(self, task):
        return datetime.now(self.tz).strftime("%H:%M:%S")

@click.group()
def cli():
    """iCloud Yashirin Email Menedjeri - Jadval asosida generatsiya"""
    pass

async def _generate(total: int, batch_size: int, delay: float, max_retries: int):
    async with RichHideMyEmail() as hme:
        with Progress(
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            MoscowTimeColumn(),
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Generatsiya qilinmoqda...", total=total)
            remaining = total
            
            while remaining > 0:
                current_batch = min(batch_size, remaining)
                logger.info(f"Partiya ishlayapti: {current_batch} ta email (qolgan: {remaining})")
                
                emails = []
                for _ in range(current_batch):
                    email = await hme._generate_one()
                    if email:
                        emails.append(email)
                        progress.update(task, advance=1)
                    await asyncio.sleep(5)  # Har bir email orasidagi kutish vaqti
                
                remaining -= len(emails)
                
                if remaining > 0:
                    logger.info(f"Keyingi partiyadan oldin {delay} soat kutish...")
                    await asyncio.sleep(delay * 3600)

            if emails:
                await hme._save_emails_to_file(emails)

async def _list(active: bool, search: Optional[str]):
    async with RichHideMyEmail() as hme:
        await hme.list_emails(active=active, search=search)

def run_async(async_func, *args):
    """Asinxron funksiyalarni boshqarish uchun yordamchi"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_func(*args))
    except KeyboardInterrupt:
        logger.warning("Operatsiya foydalanuvchi tomonidan to'xtatildi")
        print("\n✗ Operatsiya to'xtatildi!")
    except Exception as e:
        logger.error(f"Xato: {str(e)}", exc_info=True)
        print(f"\n✗ Xato: {str(e)}")
    finally:
        loop.close()

@click.command()
@click.option("--total", default=5, help="Generatsiya qilinadigan email soni", type=int)
@click.option("--batch-size", default=5, help="Har bir partiyadagi email soni", type=int)
@click.option("--delay", default=1, help="Partiyalar orasidagi kutish vaqti (soat)", type=float)
@click.option("--max-retries", default=3, help="Maksimal qayta urinishlar soni", type=int)
def generate(total: int, batch_size: int, delay: float, max_retries: int):
    """Email manzillarini jadval asosida generatsiya qilish"""
    logger.info(f"Generatsiya boshlanmoqda: jami={total}, partiyada={batch_size}, kutish={delay} soat")
    run_async(_generate, total, batch_size, delay, max_retries)

@click.command()
@click.option("--active/--inactive", default=True, help="Faol/Nofaol emaillarni filtrlash")
@click.option("--search", default=None, help="Yorliq bo'yicha qidiruv")
def list(active: bool, search: Optional[str]):
    """Mavjud email manzillarini ko'rsatish"""
    logger.info(f"Email ro'yxati ko'rsatilmoqda: active={active}, search={search}")
    run_async(_list, active, search)

cli.add_command(list, name="list")
cli.add_command(generate, name="generate")

if __name__ == "__main__":
    cli()
