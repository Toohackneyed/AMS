@echo off
cd /d "C:\Users\Identitech\Documents\AMS\AMS"
:: Activate virtual environment
call env\Scripts\activate
:: Start Django server in background
start /b python manage.py runserver_plus 192.168.0.50:8000 --cert-file=cert.pem --key-file=key.pem
:: Wait a bit for the server to boot
timeout /t 5 /nobreak >nul
:: Open the browser
start msedge "https://192.168.0.50:8000"
pause