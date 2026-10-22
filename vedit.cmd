@echo off
rem Video Edit Studio on Windows (the Mac/Git Bash twin is ./vedit). e.g.  vedit doctor  /  vedit studio
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0tools\vedit.py" %*
