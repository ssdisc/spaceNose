"""
合成生物标志物数据集生成器

基于 NASA PDS 行星大气数据生成合成传感器响应数据
用于训练星际嗅探者的深度学习模型

目标气体: CH4, PH3, SO2, H2S, CO2, VOCs
分类标签: mars, venus, comet, earth_life, background
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
SYNTHETIC_DIR = DATASETS_DIR / "synthetic"


@dataclass
class SensorConfig:
    """传感器配置"""
    name: str
    target_gas: str
    sensitivity_range: Tuple[float, float]  # (min, max) 响应范围
    noise_std: float = 0.05  # 噪声标准差
    drift_rate: float = 0.01  # 漂移率
    cross_sensitivity: Dict[str, float] = field(default_factory=dict)  # 交叉敏感性


# 传感器阵列配置 (模拟 MQ 系列传感器)
SENSOR_ARRAY = [
    SensorConfig(
        name="MQ4_CH4",
        target_gas="CH4",
        sensitivity_range=(200, 10000),  # ppm
        noise_std=0.08,
        cross_sensitivity={"H2": 0.3, "CO": 0.1, "alcohol": 0.2}
    ),
    SensorConfig(
        name="MQ136_H2S",
        target_gas="H2S",
        sensitivity_range=(1, 100),  # ppm
        noise_std=0.1,
        cross_sensitivity={"SO2": 0.4, "NH3": 0.2, "CO": 0.1}
    ),
    SensorConfig(
        name="MQ135_SO2",
        target_gas="SO2",
        sensitivity_range=(10, 1000),  # ppm
        noise_std=0.1,
        cross_sensitivity={"H2S": 0.3, "NH3": 0.5, "CO2": 0.2}
    ),
    SensorConfig(
        name="MQ135_CO2",
        target_gas="CO2",
        sensitivity_range=(400, 10000),  # ppm
        noise_std=0.05,
        cross_sensitivity={"alcohol": 0.2, "NH3": 0.3}
    ),
    SensorConfig(
        name="MQ2_VOC",
        target_gas="VOC",
        sensitivity_range=(100, 10000),  # ppm
        noise_std=0.12,
        cross_sensitivity={"CH4": 0.4, "H2": 0.5, "CO": 0.3}
    ),
    SensorConfig(
        name="PH3_MOX",
        target_gas="PH3",
        sensitivity_range=(0.01, 10),  # ppm
        noise_std=0.15,
        cross_sensitivity={"H2S": 0.5, "NH3": 0.4, "arsine": 0.6}
    ),
]


@dataclass
class PlanetaryScenario:
    """行星场景配置"""
    label: str
    description: str
    gas_concentrations: Dict[str, Tuple[float, float]]  # (mean, std)
    probability_weight: float = 1.0


# 行星场景定义
PLANETARY_SCENARIOS = {
    "mars": PlanetaryScenario(
        label="mars",
        description="火星大气 - CH4 生物标志物探测",
        gas_concentrations={
            "CH4": (0.5, 0.3),       # ppb -> 转换为传感器响应
            "CO2": (9500, 500),      # ppm (95%)
            "H2S": (0.01, 0.005),    # 极低
            "SO2": (0.01, 0.005),    # 极低
            "PH3": (0.0, 0.001),     # 不存在
            "VOC": (10, 5),          # 低
        },
        probability_weight=1.0
    ),
    "venus": PlanetaryScenario(
        label="venus",
        description="金星大气 - PH3/SO2/H2S 探测",
        gas_concentrations={
            "CH4": (0.1, 0.05),      # 极低
            "CO2": (9600, 200),      # ppm (96.5%)
            "H2S": (500, 200),       # ppb -> 高
            "SO2": (150, 50),        # ppm
            "PH3": (0.5, 0.3),       # ppb 争议性探测
            "VOC": (5, 2),           # 低
        },
        probability_weight=0.8
    ),
    "comet": PlanetaryScenario(
        label="comet",
        description="彗星彗发 - 挥发物探测",
        gas_concentrations={
            "CH4": (500, 200),       # ppm 中等
            "CO2": (1000, 300),      # ppm 10%
            "H2S": (1500, 500),      # ppm 1.5%
            "SO2": (10, 5),          # ppm 低
            "PH3": (0.1, 0.05),      # ppb 极低
            "VOC": (2000, 800),      # ppm 复杂有机物高
        },
        probability_weight=0.7
    ),
    "europa": PlanetaryScenario(
        label="europa",
        description="木卫二冰下海洋 - 热液活动探测",
        gas_concentrations={
            "CH4": (0.1, 0.05),      # 极低
            "CO2": (50, 20),         # ppm 低
            "H2S": (10, 5),          # ppm 热液标志
            "SO2": (0.01, 0.005),    # 极低
            "PH3": (0.0, 0.001),     # 不存在
            "VOC": (0.5, 0.2),       # 极低
        },
        probability_weight=0.7
    ),
    "titan": PlanetaryScenario(
        label="titan",
        description="土卫六大气 - 甲烷循环探测",
        gas_concentrations={
            "CH4": (50000, 10000),   # ppm 5% 液态甲烷湖
            "CO2": (10, 5),          # ppm 极低
            "H2S": (0.01, 0.005),    # 极低
            "SO2": (0.001, 0.0005),  # 极低
            "PH3": (0.0, 0.001),     # 不存在
            "VOC": (500, 200),       # ppm 复杂有机物
        },
        probability_weight=0.7
    ),
    "earth_life": PlanetaryScenario(
        label="earth_life",
        description="地球生命信号参考",
        gas_concentrations={
            "CH4": (1900, 300),      # ppb 生物源甲烷
            "CO2": (420, 50),        # ppm 当前地球
            "H2S": (50, 30),         # ppb 变化大
            "SO2": (5, 3),           # ppb 低
            "PH3": (0.01, 0.005),    # 极低
            "VOC": (500, 200),       # ppb 生物源VOC
        },
        probability_weight=1.0
    ),
    "background": PlanetaryScenario(
        label="background",
        description="背景/仪器噪声",
        gas_concentrations={
            "CH4": (0.05, 0.02),
            "CO2": (400, 20),        # 地球环境背景
            "H2S": (0.01, 0.005),
            "SO2": (0.01, 0.005),
            "PH3": (0.0, 0.001),
            "VOC": (5, 2),
        },
        probability_weight=1.5  # 更多背景样本
    ),
}


class SyntheticDatasetGenerator:
    """合成数据集生成器"""

    def __init__(
        self,
        sensors: List[SensorConfig] = None,
        scenarios: Dict[str, PlanetaryScenario] = None,
        random_seed: int = 42
    ):
        self.sensors = sensors or SENSOR_ARRAY
        self.scenarios = scenarios or PLANETARY_SCENARIOS
        self.rng = np.random.default_rng(random_seed)

    def _sensor_response(
        self,
        sensor: SensorConfig,
        gas_concentrations: Dict[str, float],
        time_index: int = 0
    ) -> float:
        """计算传感器对气体混合物的响应"""
        # 主要气体响应
        target_conc = gas_concentrations.get(sensor.target_gas, 0.0)

        # 归一化到传感器响应范围
        min_sens, max_sens = sensor.sensitivity_range
        if target_conc <= 0:
            base_response = 0.0
        else:
            # 对数响应模型 (模拟 MOS 传感器特性)
            log_conc = np.log10(max(target_conc, 1e-10))
            log_min = np.log10(max(min_sens, 1e-10))
            log_max = np.log10(max(max_sens, 1e-10))
            base_response = (log_conc - log_min) / (log_max - log_min)
            base_response = np.clip(base_response, 0.0, 1.0)

        # 交叉敏感性
        cross_response = 0.0
        for gas, sensitivity in sensor.cross_sensitivity.items():
            if gas in gas_concentrations:
                cross_conc = gas_concentrations[gas]
                if cross_conc > 0:
                    cross_response += sensitivity * np.log10(max(cross_conc, 1e-10)) / 10

        # 传感器漂移
        drift = sensor.drift_rate * time_index / 1000

        # 噪声
        noise = self.rng.normal(0, sensor.noise_std)

        # 总响应
        response = base_response + cross_response * 0.1 + drift + noise
        return float(np.clip(response, 0.0, 1.0))

    def generate_sample(
        self,
        scenario: PlanetaryScenario,
        time_index: int = 0
    ) -> Dict[str, Any]:
        """生成单个样本"""
        # 采样气体浓度
        gas_concentrations = {}
        for gas, (mean, std) in scenario.gas_concentrations.items():
            conc = self.rng.normal(mean, std)
            gas_concentrations[gas] = max(conc, 0.0)

        # 计算传感器阵列响应
        features = {}
        for sensor in self.sensors:
            response = self._sensor_response(sensor, gas_concentrations, time_index)
            features[sensor.name] = response

        # 添加原始气体浓度 (用于验证)
        raw_concentrations = {f"raw_{k}": v for k, v in gas_concentrations.items()}

        return {
            "label": scenario.label,
            "features": features,
            "concentrations": raw_concentrations,
            "time_index": time_index,
            "metadata": {
                "scenario_description": scenario.description,
            }
        }

    def generate_dataset(
        self,
        samples_per_class: int = 1000,
        include_time_series: bool = True,
        time_steps: int = 10
    ) -> List[Dict[str, Any]]:
        """生成完整数据集"""
        dataset = []

        for scenario_name, scenario in self.scenarios.items():
            # 根据权重调整样本数
            n_samples = int(samples_per_class * scenario.probability_weight)

            for i in range(n_samples):
                if include_time_series:
                    # 生成时序数据
                    for t in range(time_steps):
                        sample = self.generate_sample(scenario, time_index=i * time_steps + t)
                        sample["sequence_id"] = f"{scenario_name}_{i}"
                        sample["time_step"] = t
                        dataset.append(sample)
                else:
                    sample = self.generate_sample(scenario, time_index=i)
                    dataset.append(sample)

        # 打乱数据集
        self.rng.shuffle(dataset)
        return dataset

    def save_dataset(
        self,
        dataset: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
        format: str = "json"
    ) -> Path:
        """保存数据集"""
        if output_path is None:
            output_path = SYNTHETIC_DIR / f"biosignature_dataset.{format}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            import csv
            if not dataset:
                return output_path

            # 扁平化数据
            flat_data = []
            for sample in dataset:
                flat_sample = {"label": sample["label"]}
                flat_sample.update(sample["features"])
                flat_sample.update(sample.get("concentrations", {}))
                flat_sample["time_index"] = sample.get("time_index", 0)
                flat_data.append(flat_sample)

            fieldnames = list(flat_data[0].keys())
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_data)

        return output_path

    def get_statistics(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取数据集统计信息"""
        label_counts = {}
        feature_stats = {}

        for sample in dataset:
            label = sample["label"]
            label_counts[label] = label_counts.get(label, 0) + 1

            for feat_name, feat_value in sample["features"].items():
                if feat_name not in feature_stats:
                    feature_stats[feat_name] = []
                feature_stats[feat_name].append(feat_value)

        # 计算特征统计
        for feat_name in feature_stats:
            values = np.array(feature_stats[feat_name])
            feature_stats[feat_name] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }

        return {
            "total_samples": len(dataset),
            "label_distribution": label_counts,
            "feature_statistics": feature_stats,
            "sensors": [s.name for s in self.sensors],
            "scenarios": list(self.scenarios.keys()),
        }


def generate_and_save_synthetic_dataset(
    samples_per_class: int = 1000,
    include_time_series: bool = True,
    time_steps: int = 10,
    random_seed: int = 42
) -> Tuple[Path, Dict[str, Any]]:
    """生成并保存合成数据集的便捷函数"""
    generator = SyntheticDatasetGenerator(random_seed=random_seed)

    print(f"生成合成生物标志物数据集...")
    print(f"  - 每类样本数: {samples_per_class}")
    print(f"  - 时序数据: {include_time_series} (步数: {time_steps})")
    print(f"  - 场景: {list(generator.scenarios.keys())}")

    dataset = generator.generate_dataset(
        samples_per_class=samples_per_class,
        include_time_series=include_time_series,
        time_steps=time_steps
    )

    # 保存为 JSON 和 CSV
    json_path = generator.save_dataset(dataset, format="json")
    csv_path = generator.save_dataset(
        dataset,
        output_path=SYNTHETIC_DIR / "biosignature_dataset.csv",
        format="csv"
    )

    stats = generator.get_statistics(dataset)

    # 保存统计信息
    stats_path = SYNTHETIC_DIR / "dataset_statistics.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n数据集生成完成:")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV: {csv_path}")
    print(f"  - 统计: {stats_path}")
    print(f"  - 总样本数: {stats['total_samples']}")
    print(f"  - 标签分布: {stats['label_distribution']}")

    return json_path, stats


if __name__ == "__main__":
    # 生成数据集
    path, stats = generate_and_save_synthetic_dataset(
        samples_per_class=500,
        include_time_series=True,
        time_steps=10,
        random_seed=42
    )
