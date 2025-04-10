import asyncio
import datetime
import os
from typing import Union, List, Optional, Dict, Any
import re

from rich.text import Text
from rich.prompt import IntPrompt, Confirm
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from icloud import HideMyEmail


# Global constants
MAX_CONCURRENT_TASKS = 5  # Har bir partiya uchun standart elektron pochta soni
DELAY_HOURS = 1  # Har bir partiya uchun standart oraliq kutish vaqti


class RichHideMyEmail(HideMyEmail):
    _cookie_file = "cookie.txt"
    _generated_emails_file = "generated_emails.txt"

    def __init__(self):
        super().__init__()
        self.console = Console()
        self.table = Table()

        if os.path.exists(self._cookie_file):
            with open(self._cookie_file, "r", encoding="utf-8") as f:
                cookies = [line for line in f if not line.startswith("//")]
                if cookies:
                    self.cookies = cookies[0]
        else:
            self.console.log(
                '[bold yellow][WARNING][/] "cookie.txt" fayli topilmadi! Avtorizatsiyasiz kirish tufayli email generatsiyasi ishlamasligi mumkin.'
            )

    async def _generate_one(self) -> Union[str, None]:
        try:
            # Generate an email
            gen_res = await self.generate_email()
            if not gen_res or "success" not in gen_res or not gen_res["success"]:
                error = gen_res.get("error", {})
                err_msg = error.get("errorMessage", gen_res.get("reason", "Noma'lum xato"))
                self.console.log(f"[bold red][ERROR][/] Email generatsiya qilish muvaffaqiyatsiz. Sabab: {err_msg}")
                return None

            email = gen_res["result"]["hme"]
            self.console.log(f'[50%] "{email}" - Generatsiya qilindi')

            # Reserve the email
            reserve_res = await self.reserve_email(email)
            if not reserve_res or "success" not in reserve_res or not reserve_res["success"]:
                error = reserve_res.get("error", {})
                err_msg = error.get("errorMessage", reserve_res.get("reason", "Noma'lum xato"))
                self.console.log(f'[bold red][ERROR][/] "{email}" - Rezervatsiya muvaffaqiyatsiz. Sabab: {err_msg}')
                return None

            self.console.log(f'[100%] "{email}" - Rezervatsiya qilindi')
            return email
        except Exception as e:
            self.console.log(f"[bold red][ERROR][/] Generatsiya jarayonida xato: {str(e)}")
            return None

    async def _generate_batch(self, batch_size: int) -> List[str]:
        emails = []
        for _ in range(batch_size):
            email = await self._generate_one()
            if email:
                emails.append(email)
            # Har bir emaildan keyin 3 soniya kutish
            await asyncio.sleep(3)
        return emails

    async def _save_emails_to_file(self, emails: List[str]) -> bool:
        """Generatsiya qilingan emaillarni faylga saqlash"""
        if not emails:
            self.console.log("[yellow]Hech qanday email saqlanmadi[/]")
            return False
        
        try:
            # Fayl mavjud bo'lsa, yangi emaillarni qo'shamiz
            mode = "a" if os.path.exists(self._generated_emails_file) else "w"
            
            with open(self._generated_emails_file, mode, encoding="utf-8") as f:
                # Agar fayl bo'sh bo'lmasa, yangi qator qo'shamiz
                if mode == "a" and os.path.getsize(self._generated_emails_file) > 0:
                    f.write("\n")
                f.write("\n".join(emails))
            
            self.console.log(f'[bold green]Muvaffaqiyatli![/] {len(emails)} ta email "{self._generated_emails_file}" fayliga saqlandi')
            return True
        except Exception as e:
            self.console.log(f'[red]Faylga yozishda xato: {str(e)}[/]')
            return False

    async def generate_with_schedule(self, total_count: int, batch_size: int, delay: float) -> List[str]:
        emails = []
        remaining = total_count
        
        with Progress() as progress:
            task = progress.add_task("[green]Email generatsiya qilinmoqda...", total=total_count)
            
            while remaining > 0:
                current_batch = min(batch_size, remaining)
                self.console.log(f"{current_batch} ta email generatsiya qilinmoqda...")
                
                batch = await self._generate_batch(current_batch)
                emails.extend(batch)
                remaining -= len(batch)
                progress.update(task, advance=len(batch))
                
                if remaining > 0:
                    self.console.log(f"Keyingi partiyadan oldin {delay} soat kutish...")
                    await asyncio.sleep(delay * 3600)

        if emails:
            await self._save_emails_to_file(emails)
        else:
            self.console.log("[yellow]Hech qanday email generatsiya qilinmadi[/]")

        return emails

    async def list_emails(self, active: Optional[bool] = True, 
                         search: Optional[str] = None,
                         save_to_file: bool = False) -> List[Dict[str, Any]]:
        try:
            # Get emails from iCloud
            gen_res = await self.list_email()
            if not gen_res:
                self.console.log("[red]Serverdan javob kelmadi[/]")
                return []

            if "success" not in gen_res or not gen_res["success"]:
                error = gen_res.get("error", {})
                err_msg = error.get("errorMessage", gen_res.get("reason", "Noma'lum xato"))
                self.console.log(f"[red]Email ro'yxatini olish muvaffaqiyatsiz: {err_msg}[/]")
                return []

            # Prepare data
            table = Table(title="Yashirin Email Manzillari")
            table.add_column("No.", style="cyan")
            table.add_column("Yorliq", style="magenta")
            table.add_column("Email", style="green")
            table.add_column("Yaratilgan sana", style="blue")
            table.add_column("Holat", style="red")

            emails_data = []
            for idx, row in enumerate(gen_res["result"]["hmeEmails"], 1):
                if active is None or row["isActive"] == active:
                    label = row.get("label", "N/A")
                    if search and not re.search(search, label, re.IGNORECASE):
                        continue
                        
                    created = datetime.datetime.fromtimestamp(
                        row["createTimestamp"] / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    status = "Faol" if row["isActive"] else "Nofaol"
                    
                    # Add to table
                    table.add_row(
                        str(idx),
                        label,
                        row["hme"],
                        created,
                        "✅" if row["isActive"] else "❌",
                    )
                    
                    # Collect data for potential file save
                    emails_data.append({
                        "number": idx,
                        "label": label,
                        "email": row["hme"],
                        "created": created,
                        "status": status
                    })

            # Display table
            self.console.print(table)

            # Save to file if requested
            if save_to_file and emails_data:
                filename = "existing_emails.txt"
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        # Write CSV header
                        f.write("No.,Yorliq,Email,Yaratilgan sana,Holat\n")
                        # Write data
                        for item in emails_data:
                            f.write(f"{item['number']},{item['label']},{item['email']},{item['created']},{item['status']}\n")
                    
                    self.console.log(f'[bold green]Muvaffaqiyatli![/] {len(emails_data)} ta email "{filename}" fayliga saqlandi')
                except Exception as e:
                    self.console.log(f"[red]Faylga saqlashda xato: {str(e)}[/]")

            return emails_data

        except Exception as e:
            self.console.log(f"[red]Email ro'yxatini ko'rsatishda xato: {str(e)}[/]")
            return []


async def main():
    console = Console()
    console.rule("[bold]iCloud Yashirin Email Menedjeri[/]")
    
    async with RichHideMyEmail() as hme:
        while True:
            console.print("\n[bold]Asosiy menyu:[/]")
            console.print("1. Yangi email generatsiya qilish")
            console.print("2. Mavjud emaillarni ro'yhatini ko'rsatish")
            console.print("3. Chiqish")
            
            choice = IntPrompt.ask("Tanlovni kiriting", choices=["1", "2", "3"], default=3)
            
            if choice == 1:
                # Email generation
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
                
                await hme.generate_with_schedule(total, batch, delay)
                
            elif choice == 2:
                # Email listing
                active = Confirm.ask("Faol emaillarni ko'rsatish?", default=True)
                search = input("Qidiruv uchun kalit so'z (barchasi uchun bo'sh qoldiring): ").strip() or None
                save = Confirm.ask("TXT fayliga saqlash?", default=False)
                
                await hme.list_emails(active, search, save)
                
            elif choice == 3:
                console.print("[bold green]Xayr![/]")
                break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nFoydalanuvchi tomonidan bekor qilindi")
    except Exception as e:
        print(f"Xato yuz berdi: {str(e)}")