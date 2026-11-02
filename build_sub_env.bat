@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================================
echo ToSub - Build or update the named Conda environment sub_env
echo Project directory: %CD%
echo ==========================================================
echo.

set "CONDA_BAT="
for /f "delims=" %%F in ('where conda.bat 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%F"
if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%LOCALAPPDATA%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%LOCALAPPDATA%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%LOCALAPPDATA%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%LOCALAPPDATA%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%ProgramData%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%ProgramData%\anaconda3\condabin\conda.bat"

if not defined CONDA_BAT (
    echo [ERROR] conda.bat was not found.
    echo Open Anaconda Prompt and run this script again, or add Conda to PATH.
    goto :failure
)
if not exist "environment.yml" (
    echo [ERROR] environment.yml is missing from this folder.
    goto :failure
)
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt is missing from this folder.
    goto :failure
)

echo Using Conda: %CONDA_BAT%
echo.
echo [1/3] Creating or updating sub_env...
call "%CONDA_BAT%" run -n sub_env python -c "import sys" >nul 2>nul
if errorlevel 1 (
    call "%CONDA_BAT%" env create -n sub_env -f "environment.yml"
) else (
    call "%CONDA_BAT%" env update -n sub_env -f "environment.yml" --prune
)
if errorlevel 1 (
    echo [ERROR] Conda environment creation or update failed.
    goto :failure
)

echo.
echo [2/3] Activating sub_env and installing Python dependencies...
call "%CONDA_BAT%" activate sub_env
if errorlevel 1 (
    echo [ERROR] Could not activate sub_env.
    goto :failure
)
python -m pip install -r "requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip dependency installation failed.
    goto :failure
)

echo.
echo [3/3] Verifying imports and FFmpeg...
python verify_install.py
if errorlevel 1 (
    echo [ERROR] Installation verification failed. See messages above.
    goto :failure
)

echo.
echo [SUCCESS] sub_env is ready.
echo Next: double-click run_app_sub_env.bat
pause
exit /b 0

:failure
echo.
echo [FAILED] Review the errors above.
pause
exit /b 1
