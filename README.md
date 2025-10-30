# 星际嗅探者 - 传感器固件

## 项目信息
- **项目名称**: Interstellar Sniffer (星际嗅探者)
- **负责人**: 苏世鼎
- **功能**: STM32主控 + 多气体传感器采集与智能识别

## 硬件配置
- **主控芯片**: STM32F103C8T6 (蓝色药丸)
- **调试器**: ST-Link V2
- **传感器列表**:
  - [ ] MQ-4 (甲烷CH₄)
  - [ ] MQ-7 (一氧化碳CO)
  - [ ] MH-Z19B (二氧化碳CO₂)
  - [ ] 电化学传感器 (SO₂)
  - [ ] SHT30 (温湿度)

## 目录结构
```
firmware/
├── src/              # 源代码
│   └── main.c        # 主程序
├── include/          # 头文件
├── lib/              # 自定义库
├── test/             # 测试代码
└── platformio.ini    # PlatformIO配置
```

## 快速开始

### 方式A：无硬件开发（推荐新手）

**适用场景**: 没有开发板，先开发算法和逻辑

```bash
# 1. 编译模拟器（在PC上运行）
gcc test/sensor_simulator.c -o test/sensor_simulator.exe -lm -std=c11

# 2. 运行
./test/sensor_simulator.exe

# 3. 或直接运行脚本
./test/build_and_run.bat  # Windows
./test/build_and_run.sh   # Linux/Mac
```

**VSCode调试**:
1. 打开 `test/sensor_simulator.c`
2. 在代码行左侧点击设置断点（红点）
3. 按 `F5` 启动调试
4. 可以单步执行、查看变量值

### 方式B：真实硬件开发

**适用场景**: 有STM32开发板和ST-Link

#### 1. 编译项目
```bash
# 方法1：VSCode
点击底部状态栏的 "✓" 图标

# 方法2：命令行
pio run
```

#### 2. 上传到开发板
```bash
# 连接ST-Link后
pio run --target upload
```

#### 3. 查看串口输出
```bash
pio device monitor
# 或点击底部状态栏的 "🔌" 图标
```

## 引脚定义

### LED
- **PC13**: 板载LED (心跳指示)

### 串口 (UART1)
- **PA9**: TX (发送)
- **PA10**: RX (接收)
- 波特率: 115200

### ADC (传感器输入)
- **PA0**: ADC_CH0 - 传感器1
- **PA1**: ADC_CH1 - 传感器2
- **PA2**: ADC_CH2 - 传感器3
- **PA3**: ADC_CH3 - 传感器4

### I2C (数字传感器)
- **PB6**: SCL
- **PB7**: SDA

## 开发计划

### Phase 1: 基础框架 (当前)
- [x] PlatformIO项目初始化
- [x] 基础GPIO/UART/ADC配置
- [x] 串口printf重定向
- [ ] 第一个传感器调试

### Phase 2: 传感器集成
- [ ] MQ-4甲烷传感器驱动
- [ ] MH-Z19B CO2传感器驱动
- [ ] I2C温湿度传感器
- [ ] 传感器数据融合

### Phase 3: 智能算法集成
- [ ] 接入薛皓林的AI模型
- [ ] 数据预处理与滤波
- [ ] 异常检测逻辑

### Phase 4: 通信模块
- [ ] 与茅雨霏前端对接
- [ ] ONENET/TCP数据上传
- [ ] JSON数据格式化

## 注意事项
1. 确保ST-Link驱动已安装
2. 串口号需根据实际情况修改 (platformio.ini中的monitor_port)
3. 传感器需要预热时间 (MOS传感器约3-5分钟)

## 联系方式
- 苏世鼎: [你的邮箱]
- 项目组: 星际嗅探者团队
