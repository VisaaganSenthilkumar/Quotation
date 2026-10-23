@echo off
py -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --name QuotationGenerator --windowed app.py
pause
