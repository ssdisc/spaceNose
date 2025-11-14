@echo off
chcp 65001 >nul
echo ========================================
echo   星际嗅探者 - 后端服务器启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.7或更高版本
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python环境正常
echo.

echo [2/3] 安装/更新依赖包...
cd backend
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ⚠ 警告: 部分依赖包安装失败，尝试继续运行...
) else (
    echo ✓ 依赖包安装完成
)
echo.

echo [3/3] 启动服务器...
echo.
echo ========================================
python main.py

pause

