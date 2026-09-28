@echo off
REM ---------------------------------------------------------------
REM  Network Desk - one click.
REM  Fetches the latest LinkedIn data, rebuilds the desk on this PC,
REM  and opens it. Nothing leaves the machine.
REM ---------------------------------------------------------------
setlocal
title Network Desk - refreshing
cd /d "%~dp0"

REM This PC's PATH is missing System32, so tar, netstat and timeout are not found.
REM Put the standard Windows folders back for the life of this script only.
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

set "TOKEN=%USERPROFILE%\.linkedin_token"
set "PORT=8901"

if not exist "%TOKEN%" (
  echo.
  echo   Token file not found: %TOKEN%
  echo   Create it with:  notepad %%USERPROFILE%%\.linkedin_token
  echo   paste your LinkedIn access token in, save, and run this again.
  echo.
  pause
  exit /b 1
)

REM The analysis scripts ship as pipeline.tgz. Unpack once; Windows has tar built in.
if not exist "%~dp0pipeline\build.py" (
  if exist "%~dp0pipeline.tgz" (
    echo   [setup] Unpacking the rebuild scripts...
    REM Unpacked with Python rather than tar, so it works whatever the PATH looks like.
    REM Relative paths on purpose: the script has already cd'd here, and %~dp0 ends
    REM with a backslash, which cannot be the last character of a Python raw string.
    py -c "import tarfile;tarfile.open('pipeline.tgz').extractall('.')"
    if errorlevel 1 (
      echo   Could not unpack pipeline.tgz. Tell Claude and it will send the files loose.
      pause
      exit /b 1
    )
  ) else (
    echo   pipeline.tgz is missing. Ask Claude to send it again.
    pause
    exit /b 1
  )
)

echo.
echo   [1/3] Fetching the latest data from LinkedIn...
echo.
py fetch_linkedin.py --token-file "%TOKEN%"
if errorlevel 1 (
  echo.
  echo   The fetch failed. Copy the message above ^(never your token^) into the chat.
  echo.
  pause
  exit /b 1
)

py -c "import pandas, numpy" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   [setup] Installing pandas, one time only. This takes a minute...
  py -m pip install --quiet --disable-pip-version-check pandas
  if errorlevel 1 (
    echo   Could not install pandas. Run this yourself:  py -m pip install pandas
    pause
    exit /b 1
  )
)

echo.
echo   [2/3] Rebuilding the desk...
echo.
py build_desk.py
if errorlevel 1 (
  echo.
  echo   The rebuild failed. Copy the message above into the chat.
  echo.
  pause
  exit /b 1
)

echo   [3/3] Opening...

REM Serve the page over localhost so the browser treats it as a proper site and
REM your notes and done-marks persist. Bound to 127.0.0.1, so it is reachable
REM only from this computer - never from the network.
py -c "import socket,sys;s=socket.socket();r=s.connect_ex(('127.0.0.1',%PORT%));s.close();sys.exit(0 if r==0 else 1)" >nul 2>&1
if errorlevel 1 (
  start "Network Desk server" /min py "%~dp0desk_server.py" --port %PORT%
  py -c "import time;time.sleep(3)"
)
start "" "http://localhost:%PORT%/desk.html"

echo.
echo   Done. The desk is showing data fetched just now.
echo.
py -c "import time;time.sleep(5)"
