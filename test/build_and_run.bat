@echo off
REM 编译传感器模拟器（Windows）
echo ========================================
echo 编译传感器模拟器...
echo ========================================

gcc test\sensor_simulator.c -o test\sensor_simulator.exe -lm -std=c11

if %errorlevel% == 0 (
    echo.
    echo ✓ 编译成功！
    echo.
    echo 运行程序：
    echo ----------------------------------------
    test\sensor_simulator.exe
    echo ----------------------------------------
    echo.
    pause
) else (
    echo.
    echo ✗ 编译失败！
    pause
)
