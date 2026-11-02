@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CONDA_BAT="
for /f "delims=" %%F in ('where conda.bat 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%F"
if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%LOCALAPPDATA%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%LOCALAPPDATA%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%LOCALAPPDATA%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%LOCALAPPDATA%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%ProgramData%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%ProgramData%\anaconda3\condabin\conda.bat"

if not defined CONDA_BAT (
    echo [ERROR] Conda was not found. Try launching this from Anaconda Prompt.
    goto :failure
)
call "%CONDA_BAT%" activate sub_env
if errorlevel 1 (
    echo [ERROR] Could not activate sub_env.
    echo Run build_sub_env.bat first.
    goto :failure
)

echo Running ToSub with Python:
python -c "import sys; print(sys.executable)"
python app.py
if errorlevel 1 (
    echo [ERROR] The application closed with an error.
    goto :failure
)
exit /b 0

:failure
pause
exit /b 1
