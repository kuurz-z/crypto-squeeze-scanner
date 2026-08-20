@echo off
title Quant Squeeze & Pattern Scanner
cd /d "%~dp0"
echo ===================================================
echo   QUANT SQUEEZE & PATTERN SCANNER (1:1 - 1:4 RR)
echo ===================================================
echo Installing/Verifying dependencies...
pip install -r requirements.txt
echo.
echo Starting Web Server on http://127.0.0.1:8000 ...
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
