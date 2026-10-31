@echo off
title Athena Everyday Desktop Companion
echo Starting Athena Desktop Companion...
if exist "dist\athena\athena.exe" (
    start "" "dist\athena\athena.exe"
) else (
    start "" python run_athena.py
)
exit

