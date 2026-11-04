@echo off
title Spidy Everyday Desktop Companion
echo Starting Spidy Desktop Companion...
if exist "dist\spidy.exe" (
    start "" "dist\spidy.exe"
) else (
    start "" python run_spidy.py
)
exit
