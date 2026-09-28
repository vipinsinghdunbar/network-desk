@echo off
title Network Desk - on my phone
cd /d "%~dp0"
set "PATH=%SystemRoot%\System32;%SystemRoot%;%PATH%"
py "%~dp0desk_server.py" --port 8902 --lan
