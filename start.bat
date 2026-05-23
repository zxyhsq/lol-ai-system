@echo off
chcp 65001 >nul
title LOL比赛分析系统
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
