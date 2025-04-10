@echo off

:: Python mavjudligini tekshirish
for /f "delims=" %%P in ('python --version 2^>nul') do set "PYTHON_VERSION=%%P"
if not defined PYTHON_VERSION (
    echo Python o'rnatilmagan yoki PATH muhit o'zgaruvchisida topilmadi. Iltimos, Python-ni o'rnating.
    pause
    exit /b
)
echo %PYTHON_VERSION% topildi.

:: Virtual muhit mavjudligini tekshirish, agar yo'q bo'lsa yaratish
if not exist venv (
    echo Virtual muhit yaratilmoqda...
    python -m venv venv
)

:: Virtual muhitni faollashtirish
echo Virtual muhit faollashtirilmoqda...
call venv\Scripts\activate

:: Agar kutubxonalar o'rnatilmagan bo'lsa, ularni o'rnatish
if not exist venv\Lib\site-packages\installed (
    if exist requirements.txt (
        echo Tez o'rnatish uchun wheel o'rnatilmoqda...
        python -m pip install --upgrade pip --no-cache-dir
        python -m pip install requests wheel
        echo Kutubxonalar o'rnatilmoqda...
        python -m pip install -r requirements.txt || (
            echo Kutubxonalarni o'rnatish muvaffaqiyatsiz tugadi. Iltimos, requirements.txt faylini tekshiring.
            pause
            exit /b
        )
        echo. > venv\Lib\site-packages\installed
    ) else (
        echo requirements.txt fayli topilmadi, kutubxonalarni o'rnatish o'tkazib yuboriladi.
    )
) else (
    echo Kutubxonalar allaqachon o'rnatilgan, o'rnatish o'tkazib yuboriladi.
)

:: .env fayli mavjudligini tekshirish, agar yo'q bo'lsa .env-example dan nusxa olish
if not exist .env (
    echo Konfiguratsiya fayli nusxalanmoqda...
    copy .env-example .env
) else (
    echo .env faylini nusxalash o'tkazib yuboriladi.
)

:: Botni ishga tushirish va qayta ishga tushirish tsikli
:loop
echo Bot ishga tushirilmoqda...
venv\Scripts\python.exe main.py || (
    echo Botni ishga tushirish muvaffaqiyatsiz tugadi. 2 soniyadan keyin qayta urinilmoqda...
)
echo Dastur 2 soniyadan keyin qayta ishga tushirilmoqda...
timeout /t 2 /nobreak >nul
goto :loop