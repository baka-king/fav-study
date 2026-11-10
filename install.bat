@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   收藏学习台 - 安装依赖
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 python。
  echo 请先安装 Python 3.12 ^(安装时勾选 Add python.exe to PATH^)：
  echo   https://www.python.org/downloads/
  pause
  exit /b 1
)
python -c "import sys; print('Python', sys.version)"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
echo.
echo 安装完成。双击 launch.vbs 启动。
pause
