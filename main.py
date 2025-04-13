import asyncio
import re
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from rich.prompt import IntPrompt, Confirm

from icloud import HideMyEmail
from utils.logger import logger
from utils.helpers import TimeHelper
from config.settings import config

class RichHideMyEmail(HideMyEmail):
    def __init__(self):
        super().__init__()
        self.console = Console()
        self.time_helper = TimeHelper()
        self.print_lock = threading.Lock()
        self._load_cookies()
        self._setup_directories()

    def _get_current_time(self) -> str:
        """Hozirgi vaqtni formatlangan holda qaytaradi"""
        return datetime.now().strftime("%m/%d/%y %H:%M:%S MSK")

    def _print_with_timestamp(self, *args, **kwargs):
        """Vaqt logosi bilan chiqarish"""
        timestamp = f"[  {self._get_current_time()}  ] [bold white]|[/]"
        with self.print_lock:
            self.console.print(f"[bold cyan]{timestamp}[/]", *args, **kwargs)

    def _setup_directories(self):
        try:
            backup_dir = Path(config.get("DEFAULT", "backup_dir"))
            backup_dir.mkdir(exist_ok=True)
            self._print_with_timestamp("[green]✓[/] Backups papkasi yaratildi")
        except Exception as e:
            self._print_with_timestamp(f"[red]✗ Xato:[/] {str(e)}")

    def _load_cookies(self):
        cookie_file = Path(config.get("DEFAULT", "cookie_file"))
        try:
            if cookie_file.exists():
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies = [line.strip() for line in f if line.strip()]
                    if cookies:
                        self.cookies = cookies[0]
                        self._print_with_timestamp("[green]✓[/] Cookie faylidan ma'lumotlar yuklandi")
                    else:
                        self._print_with_timestamp('[yellow][!] Cookie fayli bo\'sh')
            else:
                self._print_with_timestamp('[yellow][!] Cookie fayli topilmadi')
        except Exception as e:
            self._print_with_timestamp(f'[red]✗ Xato:[/] {str(e)}')

    async def _generate_one(self, retry_count: int = 0) -> Union[str, None]:
        """Bitta email generatsiya qilish va zaxiralash"""
        try:
            # Email generatsiya qilish
            gen_res = await self.generate_email()
            
            # Server javobini tekshirish
            if not gen_res or not gen_res.get("success"):
                error = gen_res.get("error", {}) if gen_res else {}
                err_msg = error.get("errorMessage", "Noma'lum xato")
                
                # Limit xatosini aniqlash
                if any(keyword in err_msg.lower() for keyword in ["limit", "maximum", "5 per hour", "too many"]):
                    self._print_with_timestamp("[yellow]⚠️ Ogohlantirish:[/] 5 talik limitga yetdingiz [bold cyan](kuting ...)[/]")
                    return None
                
                self._print_with_timestamp(f"[red]✗ Xato:[/] {err_msg}")
                if retry_count < config.getint("DEFAULT", "max_retries"):
                    await asyncio.sleep(config.getint("DEFAULT", "retry_delay"))
                    return await self._generate_one(retry_count + 1)
                return None

            email = gen_res["result"]["hme"]
            self._print_with_timestamp(f"[bold green]✓[/] [bold blue]Pochta generatsiya qilindi:[/] {email}")

            # Emailni zaxiralash
            reserve_res = await self.reserve_email(email)
            
            # Zaxiralash javobini tekshirish
            if not reserve_res or not reserve_res.get("success"):
                error = reserve_res.get("error", {}) if reserve_res else {}
                err_msg = error.get("errorMessage", "Noma'lum xato")
                
                # Limit xatosini aniqlash
                if any(keyword in err_msg.lower() for keyword in ["limit", "maximum", "5 per hour", "too many"]):
                    self._print_with_timestamp("[yellow]⚠️ Ogohlantirish:[/] 5 talik limitga yetdingiz [bold cyan](kuting ...)[/]")
                    return None
                
                self._print_with_timestamp(f"[red]✗ Xato:[/] {err_msg}")
                if retry_count < config.getint("DEFAULT", "max_retries"):
                    await asyncio.sleep(config.getint("DEFAULT", "retry_delay"))
                    return await self._generate_one(retry_count + 1)
                return None

            self._print_with_timestamp(f"[bold green]✓✓[/] [bold blue]Pochta zaxiralandi:[/] {email}")
            return email
            
        except Exception as e:
            self._print_with_timestamp(f"[red]✗ Xato:[/] {str(e)}")
            if retry_count < config.getint("DEFAULT", "max_retries"):
                await asyncio.sleep(config.getint("DEFAULT", "retry_delay"))
                return await self._generate_one(retry_count + 1)
            return None

    async def _generate_batch(self, batch_size: int, progress: Progress, task_id: int) -> List[str]:
        emails = []
        for _ in range(batch_size):
            email = await self._generate_one()
            if email:
                emails.append(email)
                progress.update(task_id, advance=1)
            await asyncio.sleep(config.getint("DEFAULT", "time_between_accounts"))
        return emails

    async def _save_emails_to_file(self, emails: List[str]) -> bool:
        if not emails:
            self._print_with_timestamp("[yellow][!] Saqlanadigan email yo'q")
            return False
        
        try:
            emails_file = Path(config.get("DEFAULT", "generated_emails_file"))
            if emails_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = Path(config.get("DEFAULT", "backup_dir")) / f"generated_emails_{timestamp}.bak"
                emails_file.rename(backup_path)

            with open(emails_file, "w", encoding="utf-8") as f:
                f.write("\n".join(emails))
            
            self._print_with_timestamp(f'[green]✓[/] {len(emails)} ta email saqlandi')
            return True
        except Exception as e:
            self._print_with_timestamp(f'[red]✗ Xato:[/] {str(e)}')
            return False

    async def generate_with_schedule(self, total_count: int, batch_size: int) -> List[str]:
        emails = []
        remaining = total_count
        
        with Progress(
            "[progress.description]{task.description}",
            "[progress.percentage]",
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]============Yuklanmoqda============", total=total_count)
            
            while remaining > 0:
                current_batch = min(batch_size, remaining)
                self._print_with_timestamp(f"[bold]Jarayonda:[/] {current_batch} ta email")
                
                batch = await self._generate_batch(current_batch, progress, task)
                emails.extend(batch)
                remaining -= len(batch)

                progress.update(task, completed=total_count - remaining)
                
                if remaining > 0:
                    delay = config.getint("DEFAULT", "delay_hours")
                    delay_seconds = delay * 3600
                    while delay_seconds > 0:
                        hours, minutes, seconds = self.time_helper.format_seconds(delay_seconds)
                        progress.update(
                            task,
                            description=(
                                f"[bold cyan] [Kutish vaqti qoldi [/]"
                                f"[bold white]{hours:02d}:{minutes:02d}:{seconds:02d}[/] [bold cyan]... ][/]"
                            )
                        )
                        await asyncio.sleep(1)
                        delay_seconds -= 1

        if emails:
            await self._save_emails_to_file(emails)
        else:
            self._print_with_timestamp("\n[yellow]Ogohlantirish:[/] Email generatsiya qilinmadi")

        return emails

    async def list_emails(
        self, 
        active: Optional[bool] = True, 
        search: Optional[str] = None,
        save_to_file: bool = False
    ) -> List[Dict[str, Any]]:
        try:
            self._print_with_timestamp("[bold cyan]Email ro'yxati yuklanmoqda...[/]")
            
            gen_res = await self.list_email()
            if not gen_res:
                self._print_with_timestamp("[red]✗ Server javob bermadi[/]")
                return []

            if "success" not in gen_res or not gen_res["success"]:
                error = gen_res.get("error", {})
                err_msg = error.get("errorMessage", "Noma'lum xato")
                self._print_with_timestamp(f"[red]✗ Xato:[/] {err_msg}")
                return []

            table = Table(title="Yashirin Email Manzillari", show_header=True, header_style="bold magenta")
            table.add_column("№", style="cyan")
            table.add_column("Yorliq", style="magenta")
            table.add_column("Pochta", style="green")
            table.add_column("Yaratilgan sana", style="blue")
            table.add_column("Holat", style="white")

            emails_data = []
            for idx, row in enumerate(gen_res["result"]["hmeEmails"], 1):
                if active is None or row["isActive"] == active:
                    label = row.get("label", "N/A")
                    if search and not re.search(search, label, re.IGNORECASE):
                        continue
                        
                    created = self.time_helper.timestamp_to_str(row["createTimestamp"])
                    status = "✅ Faol" if row["isActive"] else "❌ No faol"
                    
                    table.add_row(str(idx), label, row["hme"], created, status)
                    emails_data.append({
                        "number": idx,
                        "label": label,
                        "email": row["hme"],
                        "created": created,
                        "status": status
                    })

            self._print_with_timestamp(table)
            self._print_with_timestamp(f"[green]✓[/] {len(emails_data)} ta email")

            if save_to_file and emails_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"existing_emails_{timestamp}.csv"
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write("№|Yorliq|Pochta|Yaratilgan sana|Holat\n")
                        for item in emails_data:
                            f.write(f"{item['number']}|{item['label']}|{item['email']}|{item['created']}|{item['status']}\n")
                    self._print_with_timestamp(f'[green]✓ {filename} fayliga saqlandi')
                except Exception as e:
                    self._print_with_timestamp(f"[red]✗ Xato:[/] {str(e)}")

            return emails_data

        except Exception as e:
            self._print_with_timestamp(f"[red]✗ Xato:[/] {str(e)}")
            return []

async def main():
    console = Console()
    
    title = "ICLOUD POCHTA YARATISH MENEDJERI"
    full_line = f"================{title}================"
    console.print(f"[bold cyan]{full_line}[/]")
    
    async with RichHideMyEmail() as hme:
        while True:
            console.print("\n[bold]Asosiy menyu:[/]")
            console.print("1. Yangi pochta generatsiya qilish")
            console.print("2. Mavjud pochtalar ro'yhatini olish")
            console.print("3. Chiqish")
            
            choice = IntPrompt.ask("\nTanlovni kiriting", choices=["1", "2", "3"], default=3)
            
            if choice == 1:
                console.print("\n[bold]Generatsiya parametrlarini tanlang:[/]")
                total = IntPrompt.ask("Generatsiya qilinadigan pochtalar soni", default=750)
                batch = IntPrompt.ask("Har bir partiyadagi pochtalar soni", default=5)
                await hme.generate_with_schedule(total, batch)
                
            elif choice == 2:
                console.print("\n[bold]Ro'yxat parametrlari:[/]")
                active = Confirm.ask("Faol emaillarni ko'rsatish?", default=True)
                search = input("Qidiruv uchun kalit so'z (barchasi uchun bo'sh qoldiring): ").strip() or None
                save = Confirm.ask("CSV fayliga saqlash?", default=False)
                await hme.list_emails(active, search, save)
                
            elif choice == 3:
                console.print("\n[bold green]Dastur tugatildi![/]")
                break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[red]Dastur to'xtatildi[/]")
    except Exception as e:
        print(f"\n[red]✗ Xato:[/] {str(e)}")
