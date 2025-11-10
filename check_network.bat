@echo off
chcp 65001 >nul
color 0A
echo ========================================
echo   星际嗅探者 - 网络配置检查工具
echo ========================================
echo.

echo [检查1] 查看本机IP地址
echo ----------------------------------------
ipconfig | findstr /C:"IPv4"
echo.

echo [检查2] 查看移动热点状态
echo ----------------------------------------
netsh wlan show hostednetwork
echo.

echo [检查3] 检查UDP端口8888占用情况
echo ----------------------------------------
netstat -an | findstr ":8888"
if errorlevel 1 (
    echo ✅ 端口8888未被占用
) else (
    echo ⚠️ 端口8888已被占用
)
echo.

echo [检查4] 检查HTTP端口8000占用情况
echo ----------------------------------------
netstat -an | findstr ":8000"
if errorlevel 1 (
    echo ✅ 端口8000未被占用
) else (
    echo ⚠️ 端口8000已被占用
)
echo.

echo [检查5] 测试防火墙设置
echo ----------------------------------------
echo 正在检查Python是否在防火墙白名单中...
netsh advfirewall firewall show rule name=all | findstr /C:"python"
if errorlevel 1 (
    echo ⚠️ 未找到Python防火墙规则
    echo 💡 建议：首次运行服务器时，允许Python通过防火墙
) else (
    echo ✅ Python已添加到防火墙规则
)
echo.

echo ========================================
echo   配置建议
echo ========================================
echo.
echo 📌 请在STM32代码中使用以下IP地址之一：
echo.
ipconfig | findstr /C:"IPv4" | findstr /V "127.0.0.1"
echo.
echo 📌 UDP服务器端口: 8888
echo 📌 HTTP服务器端口: 8000
echo.
echo ========================================

pause

