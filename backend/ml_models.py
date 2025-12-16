"""
星际嗅探者 - 深度学习模型架构 (Year 1)

根据项目要求实现:
- 1D-CNN: 处理传感器时序信号，实现气体快速分类
- GRU: 轻量级门控循环单元，捕捉气体释放的动态时序特征
- Tiny Autoencoder: 异常检测，通过重构误差发现未知异常模式

轻量化指标要求:
- 模型大小 < 100KB
- 推理时间 < 100ms
- 推理功耗 < 100mW (在STM32H7上)
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset

    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    np = None
    torch = None
    nn = None


# ============================================================================
# 模型配置
# ============================================================================

@dataclass
class ModelConfig:
    """模型配置，用于控制模型大小以满足轻量化要求"""
    # 输入特征数 (ch4, ph3, so2, h2s, co2, vocs)
    n_features: int = 6
    # 时序窗口长度
    seq_length: int = 16
    # 气体类别数 (mars, venus, comet, earth_life, background)
    n_classes: int = 5

    # 1D-CNN 配置
    cnn_channels: List[int] = None  # [16, 32]
    cnn_kernel_size: int = 3

    # GRU 配置
    gru_hidden_size: int = 32
    gru_num_layers: int = 1

    # Autoencoder 配置
    ae_latent_dim: int = 8
    ae_hidden_dims: List[int] = None  # [16, 8]

    # 异常阈值
    anomaly_threshold: float = 0.5

    def __post_init__(self):
        if self.cnn_channels is None:
            self.cnn_channels = [16, 32]
        if self.ae_hidden_dims is None:
            self.ae_hidden_dims = [16, 8]


# ============================================================================
# 1D-CNN 气体分类器
# ============================================================================

if _TORCH_AVAILABLE:
    class GasClassifier1DCNN(nn.Module):
        """
        轻量级1D-CNN气体分类器

        架构:
        - Conv1D层提取局部时序特征
        - BatchNorm + ReLU激活
        - 全局平均池化减少参数量
        - 全连接层输出分类结果

        设计目标: 模型大小 < 30KB
        """

        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config

            # 卷积层
            layers = []
            in_channels = config.n_features
            for out_channels in config.cnn_channels:
                layers.extend([
                    nn.Conv1d(in_channels, out_channels,
                              kernel_size=config.cnn_kernel_size,
                              padding=config.cnn_kernel_size // 2),
                    nn.BatchNorm1d(out_channels),
                    nn.ReLU(inplace=True),
                    nn.MaxPool1d(2)
                ])
                in_channels = out_channels

            self.conv_layers = nn.Sequential(*layers)

            # 计算卷积后的序列长度
            conv_seq_len = config.seq_length
            for _ in config.cnn_channels:
                conv_seq_len = conv_seq_len // 2

            # 全局平均池化 + 分类头
            self.global_pool = nn.AdaptiveAvgPool1d(1)
            self.classifier = nn.Sequential(
                nn.Linear(config.cnn_channels[-1], 16),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
                nn.Linear(16, config.n_classes)
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            前向传播

            Args:
                x: 输入张量 [batch, seq_length, n_features]

            Returns:
                logits: 分类logits [batch, n_classes]
            """
            # 转换为 [batch, features, seq_length] 用于Conv1d
            x = x.transpose(1, 2)

            # 卷积特征提取
            x = self.conv_layers(x)

            # 全局池化
            x = self.global_pool(x).squeeze(-1)

            # 分类
            logits = self.classifier(x)
            return logits

        def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """预测类别和置信度"""
            with torch.no_grad():
                logits = self.forward(x)
                probs = F.softmax(logits, dim=-1)
                predicted = torch.argmax(probs, dim=-1)
                confidence = probs.max(dim=-1).values
            return predicted, confidence


    class GasClassifierGRU(nn.Module):
        """
        轻量级GRU时序分类器

        架构:
        - 单层GRU捕捉时序依赖
        - 取最后时刻隐状态作为序列表示
        - 全连接层分类

        设计目标: 模型大小 < 20KB
        """

        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config

            self.gru = nn.GRU(
                input_size=config.n_features,
                hidden_size=config.gru_hidden_size,
                num_layers=config.gru_num_layers,
                batch_first=True,
                dropout=0 if config.gru_num_layers == 1 else 0.1
            )

            self.classifier = nn.Sequential(
                nn.Linear(config.gru_hidden_size, 16),
                nn.ReLU(inplace=True),
                nn.Linear(16, config.n_classes)
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            前向传播

            Args:
                x: 输入张量 [batch, seq_length, n_features]

            Returns:
                logits: 分类logits [batch, n_classes]
            """
            # GRU编码
            _, hidden = self.gru(x)

            # 取最后一层隐状态
            hidden = hidden[-1]

            # 分类
            logits = self.classifier(hidden)
            return logits

        def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """预测类别和置信度"""
            with torch.no_grad():
                logits = self.forward(x)
                probs = F.softmax(logits, dim=-1)
                predicted = torch.argmax(probs, dim=-1)
                confidence = probs.max(dim=-1).values
            return predicted, confidence


    class TinyAutoencoder(nn.Module):
        """
        微型自动编码器用于异常检测

        架构:
        - 编码器: 压缩输入到低维潜空间
        - 解码器: 从潜空间重建输入
        - 重构误差作为异常分数

        设计目标: 模型大小 < 15KB
        """

        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config

            input_dim = config.n_features * config.seq_length

            # 编码器
            encoder_layers = []
            in_dim = input_dim
            for hidden_dim in config.ae_hidden_dims:
                encoder_layers.extend([
                    nn.Linear(in_dim, hidden_dim),
                    nn.ReLU(inplace=True)
                ])
                in_dim = hidden_dim
            encoder_layers.append(nn.Linear(in_dim, config.ae_latent_dim))
            self.encoder = nn.Sequential(*encoder_layers)

            # 解码器
            decoder_layers = []
            in_dim = config.ae_latent_dim
            for hidden_dim in reversed(config.ae_hidden_dims):
                decoder_layers.extend([
                    nn.Linear(in_dim, hidden_dim),
                    nn.ReLU(inplace=True)
                ])
                in_dim = hidden_dim
            decoder_layers.append(nn.Linear(in_dim, input_dim))
            self.decoder = nn.Sequential(*decoder_layers)

            self.threshold = config.anomaly_threshold

        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            前向传播

            Args:
                x: 输入张量 [batch, seq_length, n_features]

            Returns:
                reconstructed: 重建张量
                latent: 潜空间表示
            """
            batch_size = x.size(0)
            x_flat = x.view(batch_size, -1)

            # 编码
            latent = self.encoder(x_flat)

            # 解码
            reconstructed = self.decoder(latent)
            reconstructed = reconstructed.view(batch_size,
                                               self.config.seq_length,
                                               self.config.n_features)

            return reconstructed, latent

        def compute_anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
            """计算异常分数（重构误差）"""
            with torch.no_grad():
                reconstructed, _ = self.forward(x)
                # 使用MSE作为重构误差
                mse = F.mse_loss(reconstructed, x, reduction='none')
                # 对每个样本求均值
                anomaly_score = mse.mean(dim=(1, 2))
            return anomaly_score

        def detect_anomaly(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            检测异常

            Returns:
                is_anomaly: 布尔张量，True表示异常
                scores: 异常分数
            """
            scores = self.compute_anomaly_score(x)
            is_anomaly = scores > self.threshold
            return is_anomaly, scores


    class HybridGasClassifier(nn.Module):
        """
        混合气体分类器 (1D-CNN + GRU)

        结合CNN的局部特征提取和GRU的时序建模能力

        设计目标: 模型大小 < 50KB
        """

        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config

            # CNN分支
            self.conv1 = nn.Conv1d(config.n_features, 16, kernel_size=3, padding=1)
            self.bn1 = nn.BatchNorm1d(16)
            self.conv2 = nn.Conv1d(16, 32, kernel_size=3, padding=1)
            self.bn2 = nn.BatchNorm1d(32)
            self.pool = nn.MaxPool1d(2)

            # GRU分支
            self.gru = nn.GRU(32, 16, batch_first=True)

            # 融合分类器
            self.classifier = nn.Sequential(
                nn.Linear(16 + 32, 24),  # GRU hidden + CNN global pool
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
                nn.Linear(24, config.n_classes)
            )

            self.global_pool = nn.AdaptiveAvgPool1d(1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            前向传播

            Args:
                x: 输入张量 [batch, seq_length, n_features]

            Returns:
                logits: 分类logits [batch, n_classes]
            """
            # CNN分支: [batch, features, seq] -> [batch, 32, seq/2]
            x_cnn = x.transpose(1, 2)
            x_cnn = self.pool(F.relu(self.bn1(self.conv1(x_cnn))))
            x_cnn = F.relu(self.bn2(self.conv2(x_cnn)))

            # CNN全局特征
            cnn_global = self.global_pool(x_cnn).squeeze(-1)  # [batch, 32]

            # GRU分支: 使用CNN特征
            x_gru = x_cnn.transpose(1, 2)  # [batch, seq/2, 32]
            _, gru_hidden = self.gru(x_gru)
            gru_hidden = gru_hidden.squeeze(0)  # [batch, 16]

            # 融合
            fused = torch.cat([cnn_global, gru_hidden], dim=-1)

            # 分类
            logits = self.classifier(fused)
            return logits

        def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """预测类别和置信度"""
            with torch.no_grad():
                logits = self.forward(x)
                probs = F.softmax(logits, dim=-1)
                predicted = torch.argmax(probs, dim=-1)
                confidence = probs.max(dim=-1).values
            return predicted, confidence


# ============================================================================
# 智能决策逻辑
# ============================================================================

@dataclass
class InferenceResult:
    """推理结果"""
    predicted_class: int
    class_name: str
    confidence: float
    probabilities: Dict[str, float]
    is_anomaly: bool
    anomaly_score: float
    decision: str  # 'compress', 'priority', 'high_sample'
    scientific_value: float
    inference_time_ms: float


class IntelligentDecisionEngine:
    """
    智能决策引擎

    根据PDF要求实现:
    - 若识别为"背景气体"且浓度稳定，执行高强度压缩（90%压缩率）
    - 若识别为"目标气体"或"未知异常"，立即标记为高优先级，触发"高采样模式"
    - 科学价值评分函数，指导数据下传优先级
    """

    # 气体类别名称
    CLASS_NAMES = ['mars', 'venus', 'comet', 'earth_life', 'background']

    # 各类别的科学价值权重
    SCIENTIFIC_VALUE_WEIGHTS = {
        'mars': 0.95,       # 火星相关 - 高价值
        'venus': 0.90,      # 金星相关 - 高价值
        'comet': 0.85,      # 彗星相关 - 中高价值
        'earth_life': 0.80, # 地球生命相关 - 参考价值
        'background': 0.10  # 背景气体 - 低价值
    }

    def __init__(self,
                 anomaly_weight: float = 0.3,
                 confidence_weight: float = 0.2,
                 class_weight: float = 0.5):
        """
        初始化决策引擎

        Args:
            anomaly_weight: 异常检测在科学价值中的权重
            confidence_weight: 置信度在科学价值中的权重
            class_weight: 类别在科学价值中的权重
        """
        self.anomaly_weight = anomaly_weight
        self.confidence_weight = confidence_weight
        self.class_weight = class_weight

    def compute_scientific_value(self,
                                  class_name: str,
                                  confidence: float,
                                  is_anomaly: bool,
                                  anomaly_score: float) -> float:
        """
        计算科学价值评分

        Returns:
            0.0 - 1.0 之间的评分，越高表示科学价值越大
        """
        # 类别价值
        class_value = self.SCIENTIFIC_VALUE_WEIGHTS.get(class_name, 0.5)

        # 异常加成
        anomaly_value = min(anomaly_score * 2, 1.0) if is_anomaly else 0.0

        # 置信度调整（高置信度更有价值）
        confidence_value = confidence

        # 综合评分
        score = (self.class_weight * class_value +
                 self.anomaly_weight * anomaly_value +
                 self.confidence_weight * confidence_value)

        return min(max(score, 0.0), 1.0)

    def make_decision(self,
                      class_name: str,
                      confidence: float,
                      is_anomaly: bool,
                      scientific_value: float) -> str:
        """
        做出智能决策

        Returns:
            'compress': 高压缩存储（背景气体）
            'normal': 正常存储
            'priority': 高优先级下传
            'high_sample': 触发高采样模式
        """
        # 未知异常 -> 高采样模式
        if is_anomaly and confidence < 0.6:
            return 'high_sample'

        # 目标气体且置信度高 -> 高优先级
        if class_name != 'background' and confidence > 0.7:
            return 'priority'

        # 目标气体但置信度中等 -> 正常
        if class_name != 'background':
            return 'normal'

        # 背景气体 -> 高压缩
        if class_name == 'background' and confidence > 0.8:
            return 'compress'

        return 'normal'


# ============================================================================
# 模型工具函数
# ============================================================================

def get_model_size_bytes(model: nn.Module) -> int:
    """获取模型大小（字节）"""
    if not _TORCH_AVAILABLE:
        return 0

    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    size = buffer.tell()
    buffer.close()
    return size


def get_model_size_kb(model: nn.Module) -> float:
    """获取模型大小（KB）"""
    return get_model_size_bytes(model) / 1024


def count_parameters(model: nn.Module) -> int:
    """统计模型参数数量"""
    return sum(p.numel() for p in model.parameters())


def measure_inference_time(model: nn.Module,
                           input_tensor: torch.Tensor,
                           warmup: int = 3,
                           repeat: int = 10) -> float:
    """
    测量推理时间

    Returns:
        平均推理时间（毫秒）
    """
    if not _TORCH_AVAILABLE:
        return 0.0

    model.eval()

    # 预热
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(input_tensor)

    # 测量
    times = []
    with torch.no_grad():
        for _ in range(repeat):
            start = time.perf_counter()
            _ = model(input_tensor)
            end = time.perf_counter()
            times.append((end - start) * 1000)

    return sum(times) / len(times)


def create_default_models(config: Optional[ModelConfig] = None) -> Dict[str, Any]:
    """
    创建默认模型集合

    Returns:
        包含所有模型的字典
    """
    if not _TORCH_AVAILABLE:
        return {}

    if config is None:
        config = ModelConfig()

    models = {
        'cnn_classifier': GasClassifier1DCNN(config),
        'gru_classifier': GasClassifierGRU(config),
        'hybrid_classifier': HybridGasClassifier(config),
        'autoencoder': TinyAutoencoder(config),
    }

    return models


def print_model_summary(models: Dict[str, nn.Module]) -> None:
    """打印模型摘要"""
    if not _TORCH_AVAILABLE:
        print("PyTorch not available")
        return

    print("=" * 60)
    print("模型轻量化指标检查 (Year 1 Requirements)")
    print("=" * 60)
    print(f"{'模型名称':<25} {'参数量':<12} {'大小(KB)':<12} {'符合<100KB':<10}")
    print("-" * 60)

    total_size = 0
    for name, model in models.items():
        params = count_parameters(model)
        size_kb = get_model_size_kb(model)
        total_size += size_kb
        status = "✓" if size_kb < 100 else "✗"
        print(f"{name:<25} {params:<12,} {size_kb:<12.2f} {status:<10}")

    print("-" * 60)
    print(f"{'总计':<25} {'':<12} {total_size:<12.2f} {'✓' if total_size < 100 else '✗':<10}")
    print("=" * 60)


# ============================================================================
# 模块检查
# ============================================================================

def is_torch_available() -> bool:
    """检查PyTorch是否可用"""
    return _TORCH_AVAILABLE


if __name__ == "__main__":
    if not _TORCH_AVAILABLE:
        print("PyTorch not installed. Run: pip install torch")
    else:
        # 测试模型
        config = ModelConfig()
        models = create_default_models(config)

        print_model_summary(models)

        # 测试推理时间
        print("\n推理时间测试 (batch_size=1, seq_length=16):")
        print("-" * 40)

        test_input = torch.randn(1, config.seq_length, config.n_features)

        for name, model in models.items():
            model.eval()
            if name == 'autoencoder':
                time_ms = measure_inference_time(
                    lambda x: model.compute_anomaly_score(x),
                    test_input
                )
            else:
                time_ms = measure_inference_time(model, test_input)
            status = "✓" if time_ms < 100 else "✗"
            print(f"{name:<25} {time_ms:.2f} ms {status}")
