# 星际嗅探者 - 机器学习实现文档

## 项目概述

本文档描述了"星际嗅探者"（CubeSat 智能气体探测载荷）项目中机器学习模块的完整实现，符合 **Year 1（轻量化星上智能识别算法）** 的技术要求。

### 核心目标

- 实现星上快速气体分类（mars/venus/comet/earth_life/background）
- 异常检测与智能决策
- 满足轻量化部署要求（模型 < 100KB，推理 < 100ms）

---

## 系统架构

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

---

## 文件结构

```
backend/
├── ml_service.py          # 核心 ML 服务（统一接口）
├── ml_models.py           # PyTorch 深度学习模型定义
├── ml_api.py              # FastAPI 路由端点
├── dataset_generator.py   # 合成数据集生成器
├── dataset_loader.py      # 统一数据集加载器
├── ml_models/             # 训练后的模型文件
│   ├── dl_gas_classifier.pt
│   └── dl_autoencoder.pt
└── ml_data/               # 训练数据缓存

datasets/
├── uci/                   # UCI Gas Sensor Array Dataset
│   ├── ethylene_methane.txt
│   ├── ethylene_CO.txt
│   └── Dataset/           # 漂移补偿数据
├── synthetic/             # 合成生物标志物数据集
│   ├── biosignature_dataset.json
│   ├── biosignature_dataset.csv
│   └── dataset_statistics.json
└── nasa_pds/              # 行星大气参考数据
    └── planetary_atmospheres.json
```

---

## 数据集

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
| 时序步长 | 10 |

**标签分布：**
```
background:  7,500 (30%)
mars:        5,000 (20%)
earth_life:  5,000 (20%)
venus:       4,000 (16%)
comet:       3,500 (14%)
```

### 3. NASA PDS 行星大气参考

包含 Mars、Venus、Comet 的大气成分数据，用于：
- 构建分类标签的科学依据
- 计算检测阈值
- 科学价值评分

---

## 深度学习模型

### 模型配置 (ModelConfig)

```python
@dataclass
class ModelConfig:
    n_features: int = 6          # 输入特征数
    seq_length: int = 16         # 时序长度
    n_classes: int = 5           # 分类类别数

    # 1D-CNN 参数
    cnn_channels: List[int] = (16, 32)
    cnn_kernel_size: int = 3

    # GRU 参数
    gru_hidden_size: int = 32
    gru_num_layers: int = 1

    # Autoencoder 参数
    ae_hidden_dim: int = 16
    ae_latent_dim: int = 8
```

### 1. GasClassifier1DCNN

轻量级 1D 卷积神经网络，用于提取时序气体信号的局部特征。

```
输入: (batch, seq_length, n_features)
  ↓
Conv1D(6→16, kernel=3) + ReLU + MaxPool
  ↓
Conv1D(16→32, kernel=3) + ReLU + AdaptiveMaxPool
  ↓
Flatten → Linear(32→5)
  ↓
输出: (batch, n_classes)
```

**参数量**: ~2,500 | **大小**: ~10 KB

### 2. GasClassifierGRU

轻量级门控循环单元，用于捕获时序依赖关系。

```
输入: (batch, seq_length, n_features)
  ↓
GRU(input=6, hidden=32, layers=1)
  ↓
取最后时刻隐藏状态
  ↓
Linear(32→5)
  ↓
输出: (batch, n_classes)
```

**参数量**: ~4,500 | **大小**: ~18 KB

### 3. HybridGasClassifier (主模型)

融合 1D-CNN 和 GRU 的混合架构，兼顾局部特征和时序依赖。

```
输入: (batch, seq_length, n_features)
         ↓
    ┌────┴────┐
    ↓         ↓
 1D-CNN     GRU
    ↓         ↓
 (32-dim)  (32-dim)
    └────┬────┘
         ↓
    Concat(64-dim)
         ↓
    Linear(64→32) + ReLU + Dropout(0.3)
         ↓
    Linear(32→5)
         ↓
输出: (batch, n_classes)
```

**参数量**: ~7,500 | **大小**: ~29 KB

### 4. TinyAutoencoder

微型自编码器，用于异常检测。

```
Encoder: Linear(6→16) → ReLU → Linear(16→8)
Decoder: Linear(8→16) → ReLU → Linear(16→6)

异常分数 = MSE(input, reconstructed)
```

**参数量**: ~500 | **大小**: ~2 KB

---

## 智能决策引擎

### 决策类型

| 决策 | 触发条件 | 操作 |
|------|----------|------|
| `compress` | background 且置信度 > 80% | 高压缩存储（90%压缩率） |
| `normal` | 目标气体，置信度中等 | 标准存储和下传 |
| `priority` | 目标气体，置信度 > 70% | 高优先级下传 |
| `high_sample` | 检测异常，置信度 < 60% | 触发高频采样模式 |

### 科学价值评分

```python
scientific_value = (
    0.5 * class_weight +      # 类别权重
    0.3 * anomaly_value +     # 异常价值
    0.2 * confidence          # 置信度
)

# 类别权重
CLASS_WEIGHTS = {
    "mars": 0.95,
    "venus": 0.90,
    "comet": 0.85,
    "earth_life": 0.80,
    "background": 0.10,
}
```

---

## API 端点

### 状态查询

```http
GET /api/ml/status
```

返回所有模型状态、数据集信息、轻量化指标。

### 数据集

```http
GET /api/ml/datasets
```

列出所有可用数据集。

### 深度学习训练

```http
POST /api/ml/dl/train/synthetic?epochs=50&batch_size=32
```

使用合成数据集训练分类器。

**参数：**
- `epochs`: 训练轮数 (10-500)
- `batch_size`: 批大小 (8-256)
- `learning_rate`: 学习率 (0.0001-0.1)
- `test_size`: 验证集比例 (0.1-0.4)

### 深度学习推理

```http
POST /api/ml/dl/predict
Content-Type: application/json

{
  "ch4": 0.5,
  "ph3": 0.01,
  "so2": 0.1,
  "h2s": 0.05,
  "co2": 400,
  "vocs": 10
}
```

**响应：**
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

### 模型指标

```http
GET /api/ml/dl/metrics
```

获取轻量化指标（模型大小、推理时间）。

---

## 轻量化性能

### 测试结果

| 指标 | 要求 | 实际值 | 状态 |
|------|------|--------|------|
| 模型大小 | < 100 KB | 29.22 KB | ✅ |
| 推理时间 | < 100 ms | 0.59 ms | ✅ |
| 验证准确率 | - | 99.80% | ✅ |
| 训练准确率 | - | 99.79% | ✅ |

### 部署目标

- **星上**: STM32H7 / FPGA
- **地面**: 标准 Python 环境

---

## 使用示例

### Python API 调用

```python
from ml_service import ml_service

# 加载模型
ml_service.load_models()

# 训练（使用合成数据集）
result = ml_service.train_dl_from_synthetic_dataset(
    epochs=50,
    batch_size=32,
    learning_rate=0.001,
)
print(f"验证准确率: {result['val_accuracy']:.4f}")

# 推理
features = {
    "ch4": 0.5,
    "ph3": 0.01,
    "so2": 150,
    "h2s": 500,
    "co2": 9600,
    "vocs": 5,
}
prediction = ml_service.predict_with_decision(features)
print(f"分类: {prediction['classification']['class_name']}")
print(f"决策: {prediction['decision']['action']}")
```

### 数据集加载

```python
from dataset_loader import UnifiedDatasetLoader

loader = UnifiedDatasetLoader()

# 加载合成数据集
X, y, label_map = loader.load_for_training("synthetic")
print(f"样本数: {len(X)}, 特征数: {X.shape[1]}")

# 行星大气参考
ref = loader.get_planetary_reference()
mars_info = ref.get_planet_info("mars")
print(f"火星 CH4 基线: {mars_info['atmosphere']['trace_components_ppb']['CH4']}")
```

---

## 气体覆盖矩阵

| 目标气体 | 生物标志意义 | UCI Dataset | Synthetic | 状态 |
|----------|--------------|-------------|-----------|------|
| CH₄ (甲烷) | 火星生命指标 | ✅ | ✅ | 完全覆盖 |
| PH₃ (磷化氢) | 金星生命争议 | ❌ | ✅ | 合成覆盖 |
| SO₂ (二氧化硫) | 火山/金星大气 | ❌ | ✅ | 合成覆盖 |
| H₂S (硫化氢) | 彗星/金星 | ❌ | ✅ | 合成覆盖 |
| CO₂ (二氧化碳) | 行星大气主成分 | ❌ | ✅ | 合成覆盖 |
| VOCs | 复杂有机物 | ✅ Ethylene | ✅ | 完全覆盖 |

---

## 后续优化方向

1. **模型量化**: INT8 量化进一步减小模型大小
2. **知识蒸馏**: 大模型指导小模型训练
3. **在线学习**: 支持星上增量学习
4. **真实数据**: 集成实际传感器数据进行微调
5. **ONNX 导出**: 支持跨平台部署

---

## 参考资料

- [UCI Gas Sensor Array Dataset](https://archive.ics.uci.edu/dataset/322/gas+sensor+array+under+dynamic+gas+mixtures)
- [NASA PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- 项目 PDF: 立方星"星际嗅探者"计划 - 基于智能嗅觉的多星体气体探测任务

---

*文档版本: 1.0 | 更新时间: 2025-12-14*
