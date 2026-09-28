@echo off
REM ---------------------------------------------------------------
REM  Network Desk - reachable from anywhere, without uploading it.
REM
REM  Gives you an https:// address for your phone from anywhere in the
REM  world. The desk and your data stay on this PC; only the page is
REM  relayed, and it cannot be indexed or reached without the URL.
REM
REM  A password is required. The address is public to anyone who has
REM  it, and the desk holds message excerpts from real conversations.
REM ---------------------------------------------------------------
setlocal
title Network Desk - tunnel
cd /d "%~dp0"
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

set "PORT=8901"

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo.
  echo   cloudflared is not installed. Install it once with either:
  echo.
  echo     winget install --id Cloudflare.cloudflared
  echo.
  echo   or download cloudflared-windows-amd64.exe from
  echo     github.com/cloudflare/cloudflared/releases/latest
  echo   and drop it in this folder.
  echo.
  pause
  exit /b 1
)

if not exist "site\desk.html" (
  echo.
  echo   No site\desk.html yet. Run "Refresh Network Desk" first.
  echo.
  pause
  exit /b 1
)

REM Stored in a plain text file next to the scripts rather than on the command
REM line, so the password does not sit in your shell history. The file is
REM listed in .gitignore, same as the token file. Treat it as a secret: do not
REM rename it to something that stops matching that rule.
if not exist "%~dp0desk-password.txt" (
  echo.
  echo   Choose a password for the tunnel. It is asked for once, now.
  echo   Anything you can type on a phone keyboard, but not a word someone
  echo   could guess from the name of this tool.
  echo.
  set /p "ND_PASSWORD=   Password: "
  echo %ND_PASSWORD%>"%~dp0desk-password.txt"
  set "ND_PASSWORD="
  echo.
)

REM Prefer the file over the environment: it is the same value either way, but
REM this keeps it out of the task list that `ps` prints to the whole machine.
for /f "usebackq delims=" %%p in ("%~dp0desk-password.txt") do set "ND_PASSWORD=%%p"

py -c "import socket,sys;s=socket.socket();r=s.connect_ex(('127.0.0.1',%PORT%));s.close();sys.exit(0 if r==0 else 1)" >nul 2>&1
if errorlevel 1 (
  echo   Starting the desk server...
  start "Network Desk server" /min py "%~dp0desk_server.py" --port %PORT% --lan
  py -c "import time;time.sleep(3)"
) else (
  echo   Desk server already running on %PORT%.
)

echo   Opening the tunnel...
echo.
cloudflared tunnel --url http://localhost:%PORT%
echo.
echo   The tunnel has closed. Your desk is still on this PC.
pause
