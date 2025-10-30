#!/bin/bash
# 编译传感器模拟器（Linux/Mac）

echo "========================================"
echo "编译传感器模拟器..."
echo "========================================"

gcc test/sensor_simulator.c -o test/sensor_simulator -lm -std=c11

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 编译成功！"
    echo ""
    echo "运行程序："
    echo "----------------------------------------"
    ./test/sensor_simulator
    echo "----------------------------------------"
else
    echo ""
    echo "✗ 编译失败！"
fi
