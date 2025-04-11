@echo off
cd /d "C:\Users\Identitech\Documents\AMS\AMS"
call env\Scripts\Activate
start /b python manage.py runserver_plus 192.168.0.50:8000 --cert-file=cert.pem --key-file=key.pem
timeout /t 5 /nobreak >nul
start msedge "https://192.168.0.50:8000"
pause
