@echo off
chcp 65001 >nul
echo ========================================
echo   星际嗅探者 - 后端服务器启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 检查依赖...
cd backend
if not exist "requirements.txt" (
    echo ❌ requirements.txt文件不存在
    pause
    exit /b 1
)

echo 正在安装/更新依赖包...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ⚠️ 依赖安装可能失败，但继续尝试启动...
)

echo.
echo [3/3] 启动服务器...
echo.
echo ========================================
echo   服务器信息
echo ========================================
echo   HTTP服务: http://localhost:8000
echo   UDP接收端口: 8888
echo   WebSocket: ws://localhost:8000/ws
echo ========================================
echo.
echo 💡 提示：
echo   1. 请确保STM32已配置正确的服务器IP
echo   2. 请确保电脑WiFi热点已开启
echo   3. 请检查防火墙是否允许UDP 8888端口
echo   4. 按Ctrl+C可以停止服务器
echo.
echo 正在启动...
echo.

python main.py

pause

