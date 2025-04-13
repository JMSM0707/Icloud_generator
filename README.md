# Icloud_generator
<p align="center"><img width=60% src="docs/header.png"></p>

HideMyEmail orqali Apple iCloud elektron pochta xabarlarini avtomatik yaratish uchun dastur!

_ICloud elektron pochta xabarlarini yaratish uchun siz faol iCloud+ obunasiga ega bo'lishingiz kerak..._

## Foydalanish

Apple sizga har 1 soatda iCloud oilangizda 5 tadan iborat elektron pochta xabarlarini yaratishga imkon beradi. Mening tajribamga ko'ra, 1 ta akkaunt uchun jami siz yaratishingiz mumkin bo'lgan iCloud elektron pochtalari miqdorini ~ 750 ga taga teng.

## Sozlash; o'rnatish
> Python 3.10+ talab qilinadi!

1. Ushbu omborni klonlash

```bash
git clone https://github.com/JMSM0707/Icloud_generator.git
```

2. Kutubxonalarni o'rnatish talablari

```bash
pip install -r requirements.txt
```
Yoki shunchaki START.bat fayliga ikki marta bosing.

3. [Cookie faylingizni saqlash](https://github.com/JMSM0707/Icloud_generator/blob/master/README.md#icloud-cookieni-olish-va-faylga-joylash)

   Buni faqat bir marta qilishingiz kerak 🙂

4. Endi skriptni quyidagi bilan ishga tushirishingiz mumkin:


**Mac uchun:**

```bash
python3 main.py
```

**Windows uchun:**

```bash
python main.py
```
Yoki shunchaki START.bat fayliga ikki marta bosing.

## iCloud cookieni olish va faylga joylash:

> Kerakli cookie-fayllarni olishning bir nechta usullari mavjud, ammo bu eng oddiy usul:

1. Chrome kengaytmasini yuklab oling [EditThisCookie](https://chromewebstore.google.com/detail/editthiscookie-v3/ojfebgpkimhlhcblbalbfjblapadhbol)

2. Kengaytmaga o'ting va kerakli eksport formatini o'rnating `Semicolon separated name=value pairs`
3. [EditThisCookie settings page](chrome-extension://fngmhnnpilhplaeedifhccceomclgfbg/options_pages/user_preferences.html)

<p align="center"><img src="docs/cookie-settings.png" width=70%></p>

3. Brauzeringizda [iCloud sozlamalari](https://www.icloud.com/settings/) ga o'ting va tizimga kiring.

4. EditThisCookie kengaytmasini bosing va cookie-fayllarni eksport qiling.

<p align="center"><img src="docs/export-cookies.png" width=70%></p>

5. Eksport qilingan cookie-fayllarni `cookie.txt` nomli faylga joylashtiring.

**PPOCHTALARNI FAYLGA SAQLASH**

Ish yakunlanganidan so'ng, dasturni qayta ishga tushurish orqali, `2. Mavjud pochtalar ro'yhatini olish` funksiyasi bilan Icloud akkauntdagi barcha pochtalar ro'yhatini faylga saqlab olishingiz mumkin!
