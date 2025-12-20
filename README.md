# 星际嗅探者 (Interstellar Sniffer) - 全栈物联网数据监控平台

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Platform](https://img.shields.io/badge/platform-STM32%20%7C%20Python%20%7C%20Vue.js-blue.svg)]()
[![ML](https://img.shields.io/badge/ML-PyTorch%20%7C%20scikit--learn-orange.svg)]()

**星际嗅探者** 是一个完整的物联网（IoT）数据采集、传输、处理和实时可视化监控系统，集成了轻量化机器学习模块用于星上智能气体识别。该项目旨在实现从底层传感器（STM32）到云端服务器（Python FastAPI），再到用户界面（Vue.js）的端到端数据链路，为气体探测任务提供一个高实时性、高可靠性的监控解决方案。

---

## 🚀 系统架构

本系统采用五层架构设计，确保了各层职责清晰，易于维护和扩展。

```
[ 硬件传感器层 ] --- (UART) ---> [ 无线通信层 ] --- (WiFi/TCP) ---> [ 后端服务层 ] --- (WebSocket) ---> [ 前端展示层 ]
|                |              |              |                |                  |                |
|  STM32F407     |              |  ESP8266     |                |  FastAPI (Python)  |                |  Vue.js + Canvas
|  (数据采集)     |              |  (数据转发)   |                |  (TCP/WebSocket/ML)|                |  (实时可视化)
```

1.  **硬件传感器层 (STM32)**: 使用 `STM32F407ZGT6` 微控制器采集模拟传感器数据，将其封装为 **PUS Telemetry**（User Data 采用JSON，便于联调）。
2.  **无线通信层 (ESP8266)**: STM32通过 `UART` 控制 `ESP8266`，并通过 `WiFi/TCP` 发送/接收 **二进制 PUS 包**。
3.  **网络中继层 (电脑WiFi热点)**: ESP8266作为TCP客户端，连接到电脑创建的WiFi热点，并将数据包发送到指定IP和端口。
4.  **后端服务层 (FastAPI)**: 运行在电脑上的 `FastAPI` 服务器。
    *   **TCP服务器** 监听指定端口，接收来自ESP8266的数据。
    *   **WebSocket服务器** 将处理后的数据（加入时间戳）实时广播给所有连接的前端客户端。
    *   **HTTP服务器** 提供前端Vue应用的静态文件访问。
    *   **ML服务** 提供气体分类、异常检测和智能决策功能。
    *   **ECSS PUS（星地应用层协议）**: 见 `docs/PUS_PROFILE.md`、`docs/PUS_RUNBOOK.md`；网关接口：`/api/pus/ingest`、`/api/pus/set_rate`、`/api/pus/events`。
5.  **前端展示层 (Vue.js)**: 浏览器中的Web应用。
    *   通过 `WebSocket` 实时接收后端推送的数据。
    *   使用 `Canvas` 绘制实时数据曲线图，并以卡片和日志形式展示数据。

---

## ✨ 核心功能

### 嵌入式端 (STM32)
- **实时采集**: 每秒采集一次ADC数据并转换为电压值。
- **数据封装**: 上行使用 **PUS TM(3/25)**；User Data 为JSON（如 `{"counter":N,"adc":X,"voltage":Y}`）。
- **稳定通信**: 增强的ESP8266驱动，支持TCP连接、普通/透传模式数据发送，并包含完整的状态反馈和错误处理。
- **配置灵活**: WiFi热点、服务器IP和端口等关键参数可在代码中轻松配置。

### 后端服务器 (FastAPI)
- **异步架构**: 基于 `asyncio` 实现异步非阻塞的TCP和WebSocket服务，性能卓越。
- **多协议支持**: 同时处理TCP数据接收、WebSocket实时广播和HTTP静态服务。
- **数据处理**: 接收数据后自动解析、验证并添加服务器时间戳。
- **多客户端管理**: 支持多个前端客户端同时连接和接收数据广播。
- **机器学习集成**: 内置轻量化ML模块，支持气体分类和异常检测。

### 前端应用 (Vue.js)
- **实时可视化**: 使用原生Canvas手绘实时曲线图，动态展示数据趋势，自动缩放坐标轴。
- **丰富的数据展示**: 通过数据卡片、滚动日志等多种形式展示最新和历史数据。
- **健壮的连接**: WebSocket客户端支持连接状态实时指示和断线自动重连。
- **现代UI设计**: 采用响应式设计，适配不同屏幕，提供渐变背景、卡片动画等良好视觉效果。

---

## 🤖 机器学习模块 (Year 1)

### 核心目标
- 实现星上快速气体分类（mars/venus/comet/earth_life/background）
- 异常检测与智能决策
- 满足轻量化部署要求（模型 < 100KB，推理 < 100ms）

### ML 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML Service Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐│
│  │  传统 ML    │  │  深度学习   │  │     智能决策引擎         ││
│  │ (sklearn)   │  │  (PyTorch)  │  │ (IntelligentDecision)    ││
│  │             │  │             │  │                          ││
│  │ • 场景分类  │  │ • 1D-CNN    │  │ • 科学价值评估           ││
│  │ • 异常检测  │  │ • GRU       │  │ • 数据优先级决策         ││
│  │ • E-Nose    │  │ • Hybrid    │  │ • 压缩/存储策略          ││
│  │             │  │ • Autoenc.  │  │                          ││
│  └─────────────┘  └─────────────┘  └──────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                      Dataset Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐│
│  │ UCI Gas     │  │ Synthetic   │  │   NASA PDS Reference     ││
│  │ Sensor      │  │ Biosignat.  │  │   (Mars/Venus/Comet)     ││
│  │ (CH4/CO)    │  │ (全气体)    │  │                          ││
│  └─────────────┘  └─────────────┘  └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 深度学习模型

| 模型 | 架构 | 参数量 | 大小 | 用途 |
|------|------|--------|------|------|
| GasClassifier1DCNN | 1D卷积网络 | ~2,500 | ~10 KB | 局部特征提取 |
| GasClassifierGRU | 门控循环单元 | ~4,500 | ~18 KB | 时序依赖捕获 |
| HybridGasClassifier | CNN+GRU混合 | ~7,500 | ~29 KB | 主分类模型 |
| TinyAutoencoder | 微型自编码器 | ~500 | ~2 KB | 异常检测 |

### 智能决策引擎

| 决策 | 触发条件 | 操作 |
|------|----------|------|
| `compress` | background 且置信度 > 80% | 高压缩存储（90%压缩率） |
| `normal` | 目标气体，置信度中等 | 标准存储和下传 |
| `priority` | 目标气体，置信度 > 70% | 高优先级下传 |
| `high_sample` | 检测异常，置信度 < 60% | 触发高频采样模式 |

### 轻量化性能

| 指标 | 要求 | 实际值 | 状态 |
|------|------|--------|------|
| 模型大小 | < 100 KB | 29.22 KB | ✅ |
| 推理时间 | < 100 ms | 0.59 ms | ✅ |
| 验证准确率 | - | 99.80% | ✅ |

---

## 📊 数据集

### 1. UCI Gas Sensor Array Dataset

| 属性 | 值 |
|------|-----|
| 来源 | [UCI ML Repository](https://archive.ics.uci.edu/dataset/322/gas+sensor+array+under+dynamic+gas+mixtures) |
| 大小 | ~1.6 GB |
| 传感器 | 16 通道 (TGS-2600/2602/2610/2620) |
| 气体 | Ethylene, Methane (CH₄), CO |
| 用途 | 真实传感器响应模式学习 |

### 2. Synthetic Biosignature Dataset

| 属性 | 值 |
|------|-----|
| 样本数 | 25,000 |
| 特征数 | 6 (传感器响应) |
| 气体覆盖 | CH₄, PH₃, SO₂, H₂S, CO₂, VOCs |
| 分类标签 | mars, venus, comet, earth_life, background |

### 3. NASA PDS 行星大气参考

包含 Mars、Venus、Comet 的大气成分数据，用于构建分类标签的科学依据。

### 气体覆盖矩阵

| 目标气体 | 生物标志意义 | UCI Dataset | Synthetic | 状态 |
|----------|--------------|-------------|-----------|------|
| CH₄ (甲烷) | 火星生命指标 | ✅ | ✅ | 完全覆盖 |
| PH₃ (磷化氢) | 金星生命争议 | ❌ | ✅ | 合成覆盖 |
| SO₂ (二氧化硫) | 火山/金星大气 | ❌ | ✅ | 合成覆盖 |
| H₂S (硫化氢) | 彗星/金星 | ❌ | ✅ | 合成覆盖 |
| CO₂ (二氧化碳) | 行星大气主成分 | ❌ | ✅ | 合成覆盖 |
| VOCs | 复杂有机物 | ✅ Ethylene | ✅ | 完全覆盖 |

---

## 🛠️ 技术栈

| 层次       | 技术/组件         | 描述                               |
| :--------- | :---------------- | :--------------------------------- |
| **嵌入式层** | `C`, `STM32 HAL`  | 使用PlatformIO进行开发的STM32固件     |
| **通信层**   | `ESP8266`         | UART, TCP, WiFi, ECSS PUS          |
| **后端层**   | `Python`, `FastAPI` | Uvicorn, asyncio, websockets       |
| **数据库层** | `MySQL`, `SQLAlchemy` | 持久化存储传感器数据，支持历史查询  |
| **ML层**     | `PyTorch`, `scikit-learn` | 深度学习分类、异常检测、智能决策 |
| **前端层**   | `Vue.js 3`, `Canvas` | JavaScript (ES6+), CSS3            |
| **开发工具** | `PlatformIO`, `VSCode` | 跨平台嵌入式开发环境               |

---

## ⚡ 5分钟快速上手指南

按照以下步骤，即可在5分钟内启动并运行整个系统。

### 1️⃣ 硬件准备与连接
- 将 `ESP8266` 模块正确连接到 `STM32F407` 开发板。
  ```
  STM32 PA2 (TX) → ESP8266 RX
  STM32 PA3 (RX) ← ESP8266 TX
  STM32 GND      → ESP8266 GND
  3.3V           → ESP8266 VCC & CH_PD (必须！)
  ```
- 将 `ST-Link` 连接到电脑和开发板。

### 2️⃣ 配置电脑WiFi热点
- **Windows**: `设置` → `网络和Internet` → `移动热点`。
- **重要**: 频段必须设置为 **2.4 GHz**，因为ESP8266不支持5GHz。
- 记下你的热点名称和密码。

### 3️⃣ 配置MySQL数据库
- 确保已安装MySQL数据库服务（[下载地址](https://dev.mysql.com/downloads/mysql/)）
- 创建/修改 `backend/.env`：
  ```env
  DB_HOST=localhost
  DB_PORT=3306
  DB_USER=root
  DB_PASSWORD=你的MySQL密码
  DB_NAME=spacenose

  TCP_HOST=0.0.0.0
  TCP_PORT=8888
  SERVER_HOST=0.0.0.0
  SERVER_PORT=8000
  ```
- 若数据库尚未创建，请在MySQL中执行 `CREATE DATABASE spacenose CHARACTER SET utf8mb4;`，应用启动时会自动建表（`sensor_data`）。

### 4️⃣ 修改STM32配置
- 打开 `src/main.c` 文件。
- 修改WiFi热点和服务器IP信息。你的服务器IP就是你电脑在热点中的IP地址，通常是 `192.168.137.1`。
  ```c
  // src/main.c
  const char* wifi_ssid = "你的热点名称";
  const char* wifi_password = "你的热点密码";
  const char* server_ip = "192.168.137.1"; // 通常是这个，如有不同请修改
  ```

### 5️⃣ 启动后端服务器
- 打开终端：
  ```bash
  cd backend
  python -m venv .venv
  .\.venv\Scripts\activate   # Windows
  pip install -r requirements.txt
  python main.py
  ```
- 若首次运行前端，请在另一个终端执行 `cd web && npm install && npm run build` 生成 `web/dist` 静态资源。
- 首次启动会自动创建 `sensor_data` 表。日志出现 `Uvicorn running on http://0.0.0.0:8000` 和 `✓ 数据库表创建成功` 即表示后端正常工作。

### 6️⃣ 编译和上传固件
- 在VSCode中，使用PlatformIO插件。
- 点击底部状态栏的 `→` (Upload) 按钮来编译和烧录程序到STM32。

### 7️⃣ 查看结果
- 程序上传成功后，STM32会自动重启并连接网络。
- 打开浏览器，访问 **`http://localhost:8000`**。
- 如果一切正常，你将看到实时更新的数据卡片、图表和日志！🚀

---

## 📁 项目文件结构

```
spaceNose/
├── src/                          # STM32源代码
│   ├── main.c                    # 主程序（采集+发送）
│   ├── sensor_manager.c/h        # 传感器管理
│   └── esp8266_driver.c/h        # ESP8266驱动
├── backend/                      # 后端服务器
│   ├── main.py                   # FastAPI服务器（TCP+WebSocket+API）
│   ├── config.py                 # 配置文件管理
│   ├── models.py                 # 数据库模型定义
│   ├── database.py               # 数据库操作
│   ├── ml_service.py             # ML服务核心（统一接口）
│   ├── ml_models.py              # PyTorch深度学习模型定义
│   ├── ml_api.py                 # ML API路由端点
│   ├── dataset_generator.py      # 合成数据集生成器
│   ├── dataset_loader.py         # 统一数据集加载器
│   ├── ml_models/                # 训练后的模型文件
│   │   ├── dl_gas_classifier.pt
│   │   ├── dl_autoencoder.pt
│   │   └── ...
│   ├── ml_data/                  # 训练数据缓存
│   ├── .env                      # 环境变量配置（需手动配置）
│   └── requirements.txt          # Python依赖
├── web/                          # 前端Vue应用
│   ├── src/
│   │   ├── App.vue               # Vue主组件
│   │   ├── views/                # 页面视图
│   │   └── components/           # UI组件
│   └── dist/                     # 构建产物
├── datasets/                     # 数据集目录
│   ├── uci/                      # UCI Gas Sensor Array
│   ├── synthetic/                # 合成生物标志物数据集
│   └── nasa_pds/                 # 行星大气参考数据
├── docs/                         # 立项/策划等PDF文档
└── README.md                     # 📍 你正在阅读的文件
```

---

## 🗄️ API 接口

### 数据查询 API

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/latest` | GET | 获取最新的实时数据（内存中） |
| `/api/data/recent?limit=100` | GET | 获取最近N条数据库记录 |
| `/api/data/hours?hours=1` | GET | 获取最近N小时的数据 |
| `/api/data/range?start=时间&end=时间` | GET | 根据时间范围查询数据 |
| `/api/stats` | GET | 获取数据统计信息 |
| `/api/data/cleanup?days=30` | DELETE | 清理N天前的旧数据 |

### 机器学习 API

| 接口 | 方法 | 说明 |
| :--- | :--- | :--- |
| `/api/ml/status` | GET | 获取所有模型状态和数据集信息 |
| `/api/ml/datasets` | GET | 列出所有可用数据集 |
| `/api/ml/dl/train/synthetic` | POST | 使用合成数据集训练分类器 |
| `/api/ml/dl/train/uci` | POST | 使用UCI真实数据集训练 |
| `/api/ml/dl/predict` | POST | 深度学习推理+智能决策 |
| `/api/ml/dl/metrics` | GET | 获取轻量化指标 |
| `/api/ml/dl/decision/explain` | GET | 解释智能决策逻辑 |

**ML推理示例：**
```bash
curl -X POST http://localhost:8000/api/ml/dl/predict \
  -H "Content-Type: application/json" \
  -d '{"features": {"ch4": 0.5, "ph3": 0.01, "so2": 0.1, "h2s": 0.05, "co2": 400, "vocs": 10}}'
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "classification": {
      "class_name": "mars",
      "confidence": 0.92,
      "probabilities": {...}
    },
    "anomaly_detection": {
      "is_anomaly": false,
      "score": 0.12
    },
    "decision": {
      "action": "priority",
      "scientific_value": 0.89,
      "description": "目标气体检测，高优先级下传"
    },
    "metrics": {
      "inference_time_ms": 0.8,
      "lightweight_compliant": true
    }
  }
}
```

访问 `http://localhost:8000/docs` 可查看完整的API文档（自动生成）。

---

## 🔬 合成数据集科学性说明

### 科学依据来源
- NASA PDS Atmospheres Node
- NASA Mars Fact Sheet / MSL Curiosity TLS
- ESA Venus Express 数据
- Rosetta 67P/C-G ROSINA 质谱数据
- NOAA 全球大气监测

### 已使用的科学数据

| 行星 | 气体 | 数值 | 来源 |
|------|------|------|------|
| Mars | CO₂ | 95.32% | NASA |
| Mars | CH₄ | 0.41 ppb (基线) | MSL Curiosity TLS |
| Venus | CO₂ | 96.5% | NASA |
| Venus | SO₂ | 150 ppm | Venus Express |
| Venus | PH₃ | <0.5-20 ppb (争议) | Greaves et al. 2020 |
| Comet | H₂S | 1.5% | Rosetta ROSINA |
| Earth | CH₄ | 1900 ppb | NOAA |

### 数据集定位
- ✅ 算法开发和初步验证的工具
- ✅ 模型架构测试
- ⚠️ 不能直接用于科学结论
- ⚠️ 需要真实传感器数据进行最终验证

---

## 🔌 MQ-3 接线与安全要点（PA5，分压 5V→3.0V）

- **接线**: MQ-3 VCC→JP3 5V；GND 共地；AO → 10kΩ（上臂）→ 中点 → PA5(ADC1_CH5) → 15kΩ（下臂）→ GND；DO 未用。
- **分压与代码**: 最大 5V 经 10k+15k 分压约 3.0V；`src/sensor_manager.c` 使用 `VOLTAGE_DIVIDER_RATIO = 5.0f/3.0f`，通道 `ADC_CHANNEL_5`。
- **上电前检查**: 万用表测 10k、15k 阻值和总阻值 24–26k；确认 VCC5 与 GND 不导通；确认 AO→10k→中点→PA5→15k→GND 方向正确。
- **上电验证**: 分压中点/PA5 电压应 <3.0V（清洁空气常见 1.8–2.5V）；串口应输出 MQ-3 状态、ADC、电压、PPM。
- **风险提示**: 裕量仅 ~0.3V，务必确保阻值与接法正确。

---

## 🗄️ 数据库集成说明

- **连接方式**: `DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<db>`，默认由 `.env` 中 `DB_*` 组合生成。
- **表结构**: 单表 `sensor_data`（自增 `id`、采样计数 `counter`、ADC/电压、MQ-3 衍生字段、`timestamp`、`source_ip`），定义见 `backend/models.py`。
- **自动建表**: 运行 `backend/main.py` 时会调用 `init_db()`，在数据库存在的前提下自动创建缺失的表。
- **清理策略**: 提供 `/api/data/cleanup?days=30` 以删除N天前数据。

---

## 📚 参考资料

- [UCI Gas Sensor Array Dataset](https://archive.ics.uci.edu/dataset/322/gas+sensor+array+under+dynamic+gas+mixtures)
- [NASA PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- Mumma, M. J., et al. (2009). "Strong Release of Methane on Mars in Northern Summer 2003." Science
- Webster, C. R., et al. (2018). "Background levels of methane in Mars' atmosphere show strong seasonal variations." Science
- Greaves, J. S., et al. (2020). "Phosphine gas in the cloud decks of Venus." Nature Astronomy
- Le Roy, L., et al. (2015). "Inventory of the volatiles on comet 67P/Churyumov-Gerasimenko from Rosetta/ROSINA." A&A

---

## 📄 文档索引

- 立项/策划材料请查看 `docs/` 目录下的PDF文件

---

*文档更新时间: 2025-12-20*
