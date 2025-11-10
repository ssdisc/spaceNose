# 星际嗅探者 - 传感器固件

## 项目信息
- **项目名称**: Interstellar Sniffer (星际嗅探者)
- **负责人**: 苏世鼎
- **功能**: STM32主控 + 多气体传感器采集与智能识别

## 硬件配置
- **主控芯片**: STM32F407ZGT6 (黑色开发板)
- **调试器**: ST-Link V2
- **WiFi模块**: ESP8266 (已连接)
- **传感器列表**:
  - [x] 模拟传感器 (ADC通道0-PA0)
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
- **PF9**: 板载LED1 (红色)
- **PF10**: 板载LED2 (绿色)

### 串口 (USART1) - 调试串口
- **PA9**: TX (发送)
- **PA10**: RX (接收)
- 波特率: 115200

### 串口 (USART2) - ESP8266通信
- **PA2**: TX → ESP8266 RX
- **PA3**: RX ← ESP8266 TX
- 波特率: 115200

### ADC (传感器输入)
- **PA0**: ADC1_CH0 - 传感器1 (已测试)
- **PA1**: ADC1_CH1 - 传感器2
- **PA4**: ADC1_CH4 - 传感器3
- **PA5**: ADC1_CH5 - 传感器4

### I2C (数字传感器)
- **PB6**: SCL
- **PB7**: SDA

### ESP8266连接
```
STM32 PA2 (TX) → ESP8266 RX
STM32 PA3 (RX) ← ESP8266 TX
STM32 GND     → ESP8266 GND
3.3V          → ESP8266 VCC
3.3V          → ESP8266 CH_PD
```

## 开发计划

### Phase 1: 基础框架 ✅ 已完成
- [x] PlatformIO项目初始化
- [x] 基础GPIO/UART/ADC配置
- [x] 串口printf重定向
- [x] LED闪烁测试
- [x] ADC传感器数据采集

### Phase 2: WiFi通信 ✅ 已完成
- [x] ESP8266硬件连接
- [x] USART2串口配置
- [x] ESP8266自动波特率检测
- [x] WiFi热点连接功能
- [x] IP地址查询
- [x] WiFi扫描功能

### Phase 3: 传感器集成 (进行中)
- [ ] MQ-4甲烷传感器驱动
- [ ] MH-Z19B CO2传感器驱动
- [ ] I2C温湿度传感器
- [ ] 传感器数据融合

### Phase 4: 智能算法集成
- [ ] 接入薛皓林的AI模型
- [ ] 数据预处理与滤波
- [ ] 异常检测逻辑

### Phase 5: 数据上传 ✅ 已完成
- [x] UDP客户端实现
- [x] JSON数据格式化
- [x] 实时数据传输到服务器

### Phase 6: 前端对接 ✅ 已完成
- [x] FastAPI后端服务器（UDP接收 + WebSocket转发）
- [x] Vue前端实时数据显示
- [x] WebSocket实时数据推送
- [x] 数据可视化（图表+日志）

## 快速开始 - WiFi连接

### 📱 1. 创建笔记本热点

**Windows：** 设置 → 网络和Internet → 移动热点
- SSID: `MyHotspot`
- 密码: `12345678`  
- **频段: 2.4GHz** ⚠️ (必须！ESP8266不支持5GHz)

### 💻 2. 修改代码

打开 `src/main.c` 第111-112行：

```c
const char* wifi_ssid = "MyHotspot";      // 改为你的热点名
const char* wifi_password = "12345678";   // 改为你的密码
```

### 🚀 3. 编译上传

```bash
pio run -t upload
pio device monitor
```

### ✅ 成功标志

```
✓ ESP8266连接成功！波特率: 115200
✓ WiFi连接成功！
+CIFSR:STAIP,"192.168.137.100"
```

详细教程请查看：[docs/快速开始-WiFi连接.md](docs/快速开始-WiFi连接.md)

## 🌐 完整数据传输方案（STM32 → 前端）

### 系统架构
```
STM32传感器 → UART → ESP8266 → WiFi → UDP服务器 → WebSocket → 前端浏览器
```

### 快速启动完整系统

#### 1️⃣ 配置STM32代码
修改 `src/main.c` 中的配置：
```c
// WiFi配置（第112-113行）
const char* wifi_ssid = "你的热点名称";
const char* wifi_password = "你的热点密码";

// 服务器配置（第124行）
const char* server_ip = "192.168.137.1";  // 你电脑的IP
```

#### 2️⃣ 检查网络配置
双击运行 `check_network.bat` 查看你的IP地址和端口占用情况

#### 3️⃣ 启动后端服务器
双击运行 `start_server.bat` 或手动运行：
```bash
cd backend
pip install -r requirements.txt
python main.py
```

#### 4️⃣ 烧录STM32程序
```bash
pio run -t upload
pio device monitor  # 查看连接状态
```

#### 5️⃣ 打开前端页面
浏览器访问 `http://localhost:8000`

### 📋 详细文档
- **[快速配置指南.md](快速配置指南.md)** - ⚡ 5分钟快速上手
- **[使用说明.md](使用说明.md)** - 📖 完整使用文档
- **工具脚本**:
  - `start_server.bat` - 一键启动后端服务器
  - `check_network.bat` - 网络配置检查工具

## 📚 文档索引

### 完整系统文档
- **[快速配置指南.md](快速配置指南.md)** - 5分钟快速部署完整系统
- **[使用说明.md](使用说明.md)** - 详细的系统架构和配置说明
- `start_server.bat` - 后端服务器启动脚本
- `check_network.bat` - 网络诊断工具

### WiFi相关
- [快速开始 - WiFi连接](docs/快速开始-WiFi连接.md) - WiFi基础连接
- [WiFi连接配置指南](docs/WiFi连接配置指南.md) - 详细配置说明
- [ESP8266故障排查指南](docs/ESP8266故障排查指南.md) - 问题诊断
- [ESP8266接线图](docs/ESP8266接线图.md) - 硬件连接

### 项目文档
- [项目立项申请书](docs/大学生创新创业训练计划项目（创新训练类）立项申请书.pdf)
- [星际嗅探者计划书](docs/立方星"星际嗅探者"计划-基于智能嗅觉的多星体气体探测任务.pdf)

## 注意事项
1. 确保ST-Link驱动已安装
2. 串口号需根据实际情况修改 (platformio.ini中的monitor_port)
3. 传感器需要预热时间 (MOS传感器约3-5分钟)
4. ESP8266必须使用3.3V供电，推荐加100uF电容
5. ESP8266的CH_PD引脚必须接3.3V

## 联系方式
- 苏世鼎: [你的邮箱]
- 项目组: 星际嗅探者团队
