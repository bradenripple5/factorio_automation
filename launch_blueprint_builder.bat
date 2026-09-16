@echo off
cd /d "%~dp0"
start "Factorio Production Blueprint Builder" pythonw.exe "%~dp0dev_blueprint_builder.py" --station-center-spacing-x 124 --station-center-spacing-y 66
