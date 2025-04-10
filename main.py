import asyncio
import datetime
import os
import re
import logging
from typing import Union, List, Optional, Dict, Any
from pathlib import Path

from rich.text import Text
from rich.prompt import IntPrompt, Confirm
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from icloud import HideMyEmail

# Log yozish uchun konfiguratsiya
logger = logging.getLogger(__name__)

# Global konstantalar
MAX_CONCURRENT_TASKS = 5  # Bir vaqtning o'zida generatsiya qilinadigan maksimal email soni
DELAY_HOURS = 1  # Partiyalar orasidagi kutish vaqti (soat)
TIME_BETWEEN_ACCOUNTS = 5  # Har bir email generatsiyasi orasidagi kutish vaqti (soniya)
MAX_RETRIES = 1  # Xatolik yuz berganda qayta urinishlar soni
RETRY_DELAY = 2  # Qayta urinishlar orasidagi kutish vaqti (soniya)

class RichHideMyEmail(HideMyEmail):
    """
    iCloud Hide My Email xizmati uchun kengaytirilgan klass.
    Rich kutubxonasi yordamida chiroyli interfeys va qo'shimcha funksionallikni taqdim etadi.
    """
    
    _cookie_file = "cookie.txt"  # Cookie ma'lumotlari saqlanadigan fayl
    _generated_emails_file = "generated_emails.txt"  # Generatsiya qilingan emaillar ro'yxati
    _backup_dir = "backups"  # Backup fayllar saqlanadigan papka

    def __init__(self):
        """Klassni ishga tushirish"""
        super().__init__()
        self.console = Console()  # Rich konsol obyekti
        self.table = Table()  # Jadval obyekti
        self._setup_directories()  # Kerakli papkalarni yaratish
        self._load_cookies()  # Cookie faylini yuklash

    def _setup_directories(self):
        """Kerakli papkalarni yaratish (agar mavjud bo'lmasa)"""
        try:
            Path(self._backup_dir).mkdir(exist_ok=True)
            logger.info("Papkalar muvaffaqiyatli yaratildi/yangilandi")
        except Exception as e:
            logger.error(f"Papkalarni yaratishda xato: {str(e)}")
            self.console.print(f"[red]✗ Papkalarni yaratishda xato:[/] {str(e)}")

    def _load_cookies(self):
        """Cookie faylini yuklash va tekshirish"""
        try:
            if os.path.exists(self._cookie_file):
                with open(self._cookie_file, "r", encoding="utf-8") as f:
                    # Fayldan cookie ma'lumotlarini o'qib olamiz
                    cookies = [line.strip() for line in f if line.strip() and not line.startswith("//")]
                    
                    if cookies:
                        self.cookies = cookies[0]
                        logger.info("Cookie fayli muvaffaqiyatli yuklandi")
                    else:
                        logger.warning("Cookie fayli bo'sh")
                        self.console.print(
                            '[bold yellow][!][/] "cookie.txt" fayli bo\'sh! Avtorizatsiyasiz kirish mumkin emas.'
                        )
            else:
                logger.warning("Cookie fayli topilmadi")
                self.console.print(
                    '[bold yellow][!][/] "cookie.txt" fayli topilmadi! Iltimos, avtorizatsiya qiling.'
                )
        except Exception as e:
            logger.error(f"Cookie faylini o'qishda xato: {str(e)}")
            self.console.print(f'[red]✗ Xato:[/] "cookie.txt" faylini o\'qishda xato: {str(e)}')

    async def _generate_one(self, retry_count: int = 0) -> Union[str, None]:
        """
        Bitta yashirin email generatsiya qilish va rezervatsiya qilish
        
        Args:
            retry_count (int): Qayta urinishlar soni
            
        Returns:
            Union[str, None]: Generatsiya qilingan email manzili yoki None (xato yuz berganda)
        """
        try:
            # 1. Email generatsiya qilish
            gen_res = await self.generate_email()
            
            # Generatsiya natijasini tekshirish
            if not gen_res or "success" not in gen_res or not gen_res["success"]:
                error = gen_res.get("error", {})
                err_msg = error.get("errorMessage", gen_res.get("reason", "Noma'lum xato"))
                logger.warning(f"Generatsiya muvaffaqiyatsiz: {err_msg}")
                self.console.print(f"[red]✗ Xato:[/] Generatsiya muvaffaqiyatsiz. Sabab: {err_msg}")
                
                # Qayta urinish (agar imkoniyat bo'lsa)
                if retry_count < MAX_RETRIES:
                    logger.info(f"Qayta urinish ({retry_count + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    return await self._generate_one(retry_count + 1)
                return None

            # 2. Email manzilini olish
            email = gen_res["result"]["hme"]
            logger.info(f"Email generatsiya qilindi: {email}")
            self.console.print(f"[green]✓[/] [yellow]Generatsiya:[/] {email}")

            # 3. Emailni rezervatsiya qilish
            reserve_res = await self.reserve_email(email)
            
            # Rezervatsiya natijasini tekshirish
            if not reserve_res or "success" not in reserve_res or not reserve_res["success"]:
                error = reserve_res.get("error", {})
                err_msg = error.get("errorMessage", reserve_res.get("reason", "Noma'lum xato"))
                logger.warning(f"Rezervatsiya muvaffaqiyatsiz ({email}): {err_msg}")
                self.console.print(f"[red]✗ Xato:[/] {email} - Rezervatsiya muvaffaqiyatsiz. Sabab: {err_msg}")
                
                # Qayta urinish (agar imkoniyat bo'lsa)
                if retry_count < MAX_RETRIES:
                    logger.info(f"Qayta urinish ({retry_count + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    return await self._generate_one(retry_count + 1)
                return None

            logger.info(f"Email muvaffaqiyatli rezervatsiya qilindi: {email}")
            self.console.print(f"[green]✓✓[/] [blue]Rezervatsiya:[/] {email}")
            return email
            
        except Exception as e:
            logger.error(f"Generatsiya jarayonida xato: {str(e)}", exc_info=True)
            self.console.print(f"[red]✗ Kritik xato:[/] {str(e)}")
            
            # Qayta urinish (agar imkoniyat bo'lsa)
            if retry_count < MAX_RETRIES:
                logger.info(f"Qayta urinish ({retry_count + 1}/{MAX_RETRIES})")
                await asyncio.sleep(RETRY_DELAY)
                return await self._generate_one(retry_count + 1)
            return None

    async def _generate_batch(self, batch_size: int) -> List[str]:
        """
        Bir partiya email generatsiya qilish
        
        Args:
            batch_size (int): Partiyadagi email soni
            
        Returns:
            List[str]: Generatsiya qilingan email manzillari ro'yxati
        """
        emails = []
        for _ in range(batch_size):
            email = await self._generate_one()
            if email:
                emails.append(email)
            # Email lar orasida kutish vaqti
            await asyncio.sleep(TIME_BETWEEN_ACCOUNTS)
        return emails

    async def _save_emails_to_file(self, emails: List[str]) -> bool:
        """
        Generatsiya qilingan email manzillarini faylga saqlash
        
        Args:
            emails (List[str]): Saqlanishi kerak bo'lgan email manzillari
            
        Returns:
            bool: Saqlash muvaffaqiyatli bo'lsa True, aks holda False
        """
        if not emails:
            logger.warning("Saqlash uchun email manzillari yo'q")
            self.console.print("[yellow][!] Hech qanday email saqlanmadi[/]")
            return False
        
        try:
            # 1. Avvalgi faylning backup nusxasini olish
            if os.path.exists(self._generated_emails_file):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(self._backup_dir, f"generated_emails_{timestamp}.bak")
                os.rename(self._generated_emails_file, backup_path)
                logger.info(f"Backup yaratildi: {backup_path}")

            # 2. Yangi email manzillarini faylga yozish
            with open(self._generated_emails_file, "w", encoding="utf-8") as f:
                f.write("\n".join(emails))
            
            logger.info(f"{len(emails)} ta email saqlandi: {self._generated_emails_file}")
            self.console.print(
                f'[green]✓[/] [bold]Muvaffaqiyatli![/] {len(emails)} ta email '
                f'"{self._generated_emails_file}" fayliga saqlandi'
            )
            return True
            
        except Exception as e:
            logger.error(f"Faylga yozishda xato: {str(e)}", exc_info=True)
            self.console.print(f'[red]✗ Faylga yozishda xato: {str(e)}[/]')
            return False

    async def generate_with_schedule(
        self, 
        total_count: int, 
        batch_size: int, 
        delay: float, 
        max_retries: int
    ) -> List[str]:
        """
        Jadval asosida email manzillarini generatsiya qilish
        
        Args:
            total_count (int): Jami generatsiya qilinadigan email soni
            batch_size (int): Har bir partiyadagi email soni
            delay (float): Partiyalar orasidagi kutish vaqti (soat)
            max_retries (int): Xatolik bo'lganda maksimal qayta urinishlar soni
            
        Returns:
            List[str]: Generatsiya qilingan barcha email manzillari ro'yxati
        """
        global MAX_RETRIES
        MAX_RETRIES = max_retries
        
        emails = []
        remaining = total_count  # Generatsiya qilinishi kerak bo'lgan qolgan email soni
        
        # Progress bari bilan ishlash
        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Generatsiya qilinmoqda...", total=total_count)
            
            while remaining > 0:
                current_batch = min(batch_size, remaining)
                logger.info(f"Partiya ishlayapti: {current_batch} ta email (qolgan: {remaining})")
                self.console.print(f"\n[bold]Partiya:[/] {current_batch} ta email generatsiya qilinmoqda...")
                
                # Partiyani generatsiya qilish
                batch = await self._generate_batch(current_batch)
                emails.extend(batch)
                remaining -= len(batch)
                progress.update(task, completed=total_count - remaining)
                
                # Agar email lar qolgan bo'lsa, keyingi partiyadan oldin kutish
                if remaining > 0:
                    logger.info(f"Keyingi partiyadan oldin {delay} soat kutish...")
                    self.console.print(f"\n[bold yellow]Kutish:[/] Keyingi partiyadan oldin {delay} soat kutish...")
                    await asyncio.sleep(delay * 3600)

        # Generatsiya natijalarini saqlash
        if emails:
            await self._save_emails_to_file(emails)
        else:
            logger.warning("Hech qanday email generatsiya qilinmadi")
            self.console.print("\n[bold yellow]Ogohlantirish:[/] Hech qanday email generatsiya qilinmadi")

        return emails

    async def list_emails(
        self, 
        active: Optional[bool] = True, 
        search: Optional[str] = None,
        save_to_file: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Mavjud email manzillarini ro'yxatini ko'rsatish
        
        Args:
            active (Optional[bool]): Faol emaillarni ko'rsatish (None bo'lsa hammasi)
            search (Optional[str]): Qidiruv so'zi (label bo'yicha)
            save_to_file (bool): Faylga saqlash kerak bo'lsa True
            
        Returns:
            List[Dict[str, Any]]: Email manzillari haqida ma'lumotlar ro'yxati
        """
        try:
            logger.info(f"Email ro'yxati ko'rsatilmoqda: active={active}, search={search}")
            
            # 1. iCloud dan email manzillarini olish
            gen_res = await self.list_email()
            if not gen_res:
                logger.error("Serverdan javob kelmadi")
                self.console.print("[red]✗ Serverdan javob kelmadi[/]")
                return []

            # 2. Natijani tekshirish
            if "success" not in gen_res or not gen_res["success"]:
                error = gen_res.get("error", {})
                err_msg = error.get("errorMessage", gen_res.get("reason", "Noma'lum xato"))
                logger.error(f"Email ro'yxatini olish muvaffaqiyatsiz: {err_msg}")
                self.console.print(f"[red]✗ Email ro'yxatini olish muvaffaqiyatsiz: {err_msg}[/]")
                return []

            # 3. Jadvalni tayyorlash
            table = Table(title="Yashirin Email Manzillari", show_header=True, header_style="bold magenta")
            table.add_column("No.", style="cyan")
            table.add_column("Yorliq", style="magenta")
            table.add_column("Email", style="green")
            table.add_column("Yaratilgan sana", style="blue")
            table.add_column("Holat", style="red")

            emails_data = []
            for idx, row in enumerate(gen_res["result"]["hmeEmails"], 1):
                # Filtrlash (faol/nofaol)
                if active is None or row["isActive"] == active:
                    label = row.get("label", "N/A")
                    
                    # Qidiruv bo'yicha filtrlash
                    if search and not re.search(search, label, re.IGNORECASE):
                        continue
                        
                    # Sana formatini o'zgartirish
                    created = datetime.datetime.fromtimestamp(
                        row["createTimestamp"] / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    status = "Faol" if row["isActive"] else "Nofaol"
                    
                    # Jadvalga qo'shish
                    table.add_row(
                        str(idx),
                        label,
                        row["hme"],
                        created,
                        "✅" if row["isActive"] else "❌",
                    )
                    
                    # Ma'lumotlarni saqlash
                    emails_data.append({
                        "number": idx,
                        "label": label,
                        "email": row["hme"],
                        "created": created,
                        "status": status
                    })

            # 4. Jadvalni ko'rsatish
            self.console.print(table)
            logger.info(f"{len(emails_data)} ta email ko'rsatildi")

            # 5. Faylga saqlash (agar kerak bo'lsa)
            if save_to_file and emails_data:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"existing_emails_{timestamp}.csv"
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        # CSV sarlavhasi
                        f.write("No.,Yorliq,Email,Yaratilgan sana,Holat\n")
                        # Ma'lumotlarni yozish
                        for item in emails_data:
                            f.write(f"{item['number']},{item['label']},{item['email']},{item['created']},{item['status']}\n")
                    
                    logger.info(f"Email ro'yxati faylga saqlandi: {filename}")
                    self.console.print(
                        f'[green]✓[/] [bold]Muvaffaqiyatli![/] {len(emails_data)} ta email '
                        f'"{filename}" fayliga saqlandi'
                    )
                except Exception as e:
                    logger.error(f"Faylga saqlashda xato: {str(e)}", exc_info=True)
                    self.console.print(f"[red]✗ Faylga saqlashda xato: {str(e)}[/]")

            return emails_data

        except Exception as e:
            logger.error(f"Email ro'yxatini ko'rsatishda xato: {str(e)}", exc_info=True)
            self.console.print(f"[red]✗ Email ro'yxatini ko'rsatishda xato: {str(e)}[/]")
            return []


async def main():
    """Asosiy dastur ishga tushirish funksiyasi"""
    console = Console()
    console.rule("[bold blue]iCloud Yashirin Email Menedjeri[/]")
    
    async with RichHideMyEmail() as hme:
        while True:
            # Asosiy menyu
            console.print("\n[bold]Asosiy menyu:[/]")
            console.print("1. Yangi pochta generatsiya qilish")
            console.print("2. Mavjud pochtalar ro'yhatini olish")
            console.print("3. Chiqish")
            
            # Foydalanuvchi tanlovi
            choice = IntPrompt.ask("\nTanlovni kiriting", choices=["1", "2", "3"], default=3)
            
            if choice == 1:
                # Email generatsiya qilish
                console.print("\n[bold]Email generatsiya parametrlari:[/]")
                total = IntPrompt.ask(
                    "Generatsiya qilinadigan email soni?",
                    default=750,
                    show_default=True
                )
                batch = IntPrompt.ask(
                    "Har bir partiyadagi email soni?",
                    default=MAX_CONCURRENT_TASKS,
                    show_default=True
                )
                delay = IntPrompt.ask(
                    "Partiyalar orasidagi vaqt (soat)?",
                    default=DELAY_HOURS,
                    show_default=True
                )
                max_retries = IntPrompt.ask(
                    "Maksimal qayta urinishlar soni?",
                    default=MAX_RETRIES,
                    show_default=True
                )
                
                await hme.generate_with_schedule(total, batch, delay, max_retries)
                
            elif choice == 2:
                # Email ro'yxatini ko'rsatish
                console.print("\n[bold]Ro'yxat parametrlari:[/]")
                active = Confirm.ask("Faol emaillarni ko'rsatish?", default=True)
                search = input("Qidiruv uchun kalit so'z (barchasi uchun bo'sh qoldiring): ").strip() or None
                save = Confirm.ask("CSV fayliga saqlash?", default=False)
                
                await hme.list_emails(active, search, save)
                
            elif choice == 3:
                # Dasturni tugatish
                console.print("\n[bold green]Dastur tugatildi![/]")
                break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[red]Dastur foydalanuvchi tomonidan to'xtatildi[/]")
    except Exception as e:
        print(f"\n[red]✗ Kritik xato: {str(e)}[/]")
