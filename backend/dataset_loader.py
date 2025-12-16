"""
数据集加载器模块

提供统一的数据集加载接口，整合：
- UCI Gas Sensor Array Dataset (CH4, CO, Ethylene)
- NASA PDS 行星大气参考数据
- 合成生物标志物数据集 (CH4, PH3, SO2, H2S, CO2, VOCs)

用于训练星际嗅探者的深度学习模型
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"


@dataclass
class DatasetInfo:
    """数据集信息"""
    name: str
    path: Path
    description: str
    n_samples: int
    n_features: int
    labels: List[str]
    feature_names: List[str]


class UCIGasSensorLoader:
    """UCI Gas Sensor Array Dataset 加载器"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (DATASETS_DIR / "uci")
        self._ethylene_methane_file = self.data_dir / "ethylene_methane.txt"
        self._ethylene_co_file = self.data_dir / "ethylene_CO.txt"

    def _parse_uci_file(
        self,
        file_path: Path,
        max_samples: Optional[int] = None,
        subsample_rate: int = 100  # 每100个样本取1个 (原始数据太大)
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """解析 UCI 数据文件"""
        if not file_path.exists():
            raise FileNotFoundError(f"UCI 数据文件不存在: {file_path}")

        features = []
        labels = []
        feature_names = [f"sensor_{i}" for i in range(16)]

        with open(file_path, "r") as f:
            for i, line in enumerate(f):
                if max_samples and len(features) >= max_samples:
                    break
                if i % subsample_rate != 0:
                    continue

                parts = line.strip().split()
                if len(parts) < 19:
                    continue

                try:
                    time_sec = float(parts[0])
                    gas1_conc = float(parts[1])  # Methane or CO
                    gas2_conc = float(parts[2])  # Ethylene
                    sensor_readings = [float(x) for x in parts[3:19]]

                    # 转换传感器读数为电阻值 (KOhm)
                    sensor_readings = [40000 / max(s, 1) for s in sensor_readings]

                    # 生成标签 (基于浓度)
                    if "methane" in file_path.name.lower():
                        if gas1_conc > 100:
                            label = "methane_high"
                        elif gas1_conc > 10:
                            label = "methane_medium"
                        else:
                            label = "background"
                    else:
                        if gas1_conc > 200:
                            label = "co_high"
                        elif gas1_conc > 50:
                            label = "co_medium"
                        else:
                            label = "background"

                    features.append(sensor_readings)
                    labels.append(label)

                except (ValueError, IndexError):
                    continue

        return np.array(features), np.array(labels), feature_names

    def load_ethylene_methane(
        self,
        max_samples: int = 10000,
        subsample_rate: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """加载 Ethylene-Methane 数据集"""
        return self._parse_uci_file(
            self._ethylene_methane_file,
            max_samples=max_samples,
            subsample_rate=subsample_rate
        )

    def load_ethylene_co(
        self,
        max_samples: int = 10000,
        subsample_rate: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """加载 Ethylene-CO 数据集"""
        return self._parse_uci_file(
            self._ethylene_co_file,
            max_samples=max_samples,
            subsample_rate=subsample_rate
        )

    def load_combined(
        self,
        max_samples: int = 20000,
        subsample_rate: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """加载合并的数据集"""
        X1, y1, names = self.load_ethylene_methane(max_samples // 2, subsample_rate)
        X2, y2, _ = self.load_ethylene_co(max_samples // 2, subsample_rate)

        X = np.vstack([X1, X2])
        y = np.concatenate([y1, y2])

        return X, y, names

    def get_info(self) -> DatasetInfo:
        """获取数据集信息"""
        return DatasetInfo(
            name="UCI Gas Sensor Array",
            path=self.data_dir,
            description="16 化学传感器阵列时序数据 (Ethylene/Methane/CO)",
            n_samples=-1,  # 动态
            n_features=16,
            labels=["methane_high", "methane_medium", "co_high", "co_medium", "background"],
            feature_names=[f"sensor_{i}" for i in range(16)]
        )


class SyntheticBiosignatureLoader:
    """合成生物标志物数据集加载器"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (DATASETS_DIR / "synthetic")
        self._json_file = self.data_dir / "biosignature_dataset.json"
        self._csv_file = self.data_dir / "biosignature_dataset.csv"
        self._stats_file = self.data_dir / "dataset_statistics.json"

    def load(
        self,
        format: str = "numpy",
        include_concentrations: bool = False
    ) -> Union[Tuple[np.ndarray, np.ndarray, List[str]], List[Dict[str, Any]]]:
        """
        加载合成数据集

        Args:
            format: "numpy" 返回 (X, y, feature_names), "raw" 返回原始字典列表
            include_concentrations: 是否包含原始气体浓度特征

        Returns:
            根据 format 参数返回不同格式的数据
        """
        if not self._json_file.exists():
            raise FileNotFoundError(f"合成数据集不存在: {self._json_file}")

        with open(self._json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if format == "raw":
            return data

        # 转换为 numpy 格式
        X = []
        y = []
        feature_names = None

        for sample in data:
            features = sample["features"]
            if feature_names is None:
                feature_names = list(features.keys())
                if include_concentrations:
                    conc_names = list(sample.get("concentrations", {}).keys())
                    feature_names.extend(conc_names)

            row = [features[name] for name in list(sample["features"].keys())]
            if include_concentrations:
                conc = sample.get("concentrations", {})
                row.extend([conc.get(name, 0) for name in list(sample.get("concentrations", {}).keys())])

            X.append(row)
            y.append(sample["label"])

        return np.array(X), np.array(y), feature_names

    def load_for_classification(
        self,
        labels: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """
        加载用于分类的数据集

        Args:
            labels: 要包含的标签列表 (None 表示全部)

        Returns:
            (X, y_encoded, label_map)
        """
        X, y, _ = self.load(format="numpy")

        # 过滤标签
        if labels:
            mask = np.isin(y, labels)
            X = X[mask]
            y = y[mask]

        # 编码标签
        unique_labels = sorted(set(y))
        label_map = {label: i for i, label in enumerate(unique_labels)}
        y_encoded = np.array([label_map[label] for label in y])

        return X, y_encoded, label_map

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据集统计信息"""
        if not self._stats_file.exists():
            return {}

        with open(self._stats_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_info(self) -> DatasetInfo:
        """获取数据集信息"""
        stats = self.get_statistics()
        return DatasetInfo(
            name="Synthetic Biosignature Dataset",
            path=self.data_dir,
            description="合成生物标志物传感器响应数据 (CH4/PH3/SO2/H2S/CO2/VOC)",
            n_samples=stats.get("total_samples", 0),
            n_features=len(stats.get("sensors", [])),
            labels=stats.get("scenarios", []),
            feature_names=stats.get("sensors", [])
        )


class PlanetaryAtmosphereReference:
    """NASA PDS 行星大气参考数据"""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (DATASETS_DIR / "nasa_pds")
        self._reference_file = self.data_dir / "planetary_atmospheres.json"
        self._data: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        """加载参考数据"""
        if self._data is None:
            if not self._reference_file.exists():
                raise FileNotFoundError(f"行星大气参考数据不存在: {self._reference_file}")
            with open(self._reference_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        return self._data

    def get_planet_info(self, planet: str) -> Dict[str, Any]:
        """获取行星大气信息"""
        data = self._load()
        return data.get("planets", {}).get(planet, {})

    def get_detection_thresholds(self) -> Dict[str, Any]:
        """获取检测阈值"""
        data = self._load()
        return data.get("detection_thresholds", {})

    def get_sensor_patterns(self) -> Dict[str, Any]:
        """获取传感器响应模式"""
        data = self._load()
        return data.get("sensor_response_patterns", {})

    def get_scientific_value(self, label: str) -> float:
        """获取科学价值评分"""
        planet_info = self.get_planet_info(label)
        return planet_info.get("scientific_value", 0.5)

    def classify_by_thresholds(
        self,
        ch4_ppb: float = 0,
        ph3_ppb: float = 0,
        so2_ppm: float = 0,
        h2s_ppb: float = 0,
        co2_percent: float = 0
    ) -> Tuple[str, float]:
        """
        基于阈值进行初步分类

        Returns:
            (predicted_label, confidence)
        """
        thresholds = self.get_detection_thresholds()

        scores = {
            "mars": 0.0,
            "venus": 0.0,
            "comet": 0.0,
            "earth_life": 0.0,
            "background": 0.0
        }

        # CH4 评分
        ch4_th = thresholds.get("CH4_ppb", {})
        if ch4_ppb > 1000:
            scores["earth_life"] += 0.4
        elif ch4_ppb > 10:
            scores["comet"] += 0.3
        elif ch4_ppb > 0.1:
            scores["mars"] += 0.3
        else:
            scores["background"] += 0.2

        # PH3 评分
        if ph3_ppb > 0.1:
            scores["venus"] += 0.4

        # SO2 评分
        if so2_ppm > 1:
            scores["venus"] += 0.3
        elif so2_ppm > 0.01:
            scores["venus"] += 0.1

        # H2S 评分
        if h2s_ppb > 1000:
            scores["comet"] += 0.3
            scores["venus"] += 0.2
        elif h2s_ppb > 100:
            scores["venus"] += 0.2

        # CO2 评分
        if co2_percent > 90:
            scores["mars"] += 0.2
            scores["venus"] += 0.2

        # 获取最高分
        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]

        # 归一化置信度
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.5

        return best_label, confidence


class UnifiedDatasetLoader:
    """统一数据集加载器"""

    def __init__(self, datasets_dir: Optional[Path] = None):
        self.datasets_dir = datasets_dir or DATASETS_DIR
        self.uci_loader = UCIGasSensorLoader(self.datasets_dir / "uci")
        self.synthetic_loader = SyntheticBiosignatureLoader(self.datasets_dir / "synthetic")
        self.planetary_ref = PlanetaryAtmosphereReference(self.datasets_dir / "nasa_pds")

    def load_for_training(
        self,
        dataset: str = "synthetic",
        **kwargs
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """
        加载训练数据

        Args:
            dataset: "synthetic", "uci", "combined"
            **kwargs: 传递给具体加载器的参数

        Returns:
            (X, y_encoded, label_map)
        """
        if dataset == "synthetic":
            return self.synthetic_loader.load_for_classification(**kwargs)
        elif dataset == "uci":
            X, y, _ = self.uci_loader.load_combined(**kwargs)
            unique_labels = sorted(set(y))
            label_map = {label: i for i, label in enumerate(unique_labels)}
            y_encoded = np.array([label_map[label] for label in y])
            return X, y_encoded, label_map
        elif dataset == "combined":
            # 合并两个数据集 (需要特征对齐)
            X_syn, y_syn, label_map_syn = self.synthetic_loader.load_for_classification()
            return X_syn, y_syn, label_map_syn  # 暂时只返回合成数据
        else:
            raise ValueError(f"未知数据集: {dataset}")

    def get_available_datasets(self) -> List[DatasetInfo]:
        """获取可用数据集列表"""
        datasets = []

        # 检查 UCI 数据集
        if (self.datasets_dir / "uci" / "ethylene_methane.txt").exists():
            datasets.append(self.uci_loader.get_info())

        # 检查合成数据集
        if (self.datasets_dir / "synthetic" / "biosignature_dataset.json").exists():
            datasets.append(self.synthetic_loader.get_info())

        return datasets

    def get_planetary_reference(self) -> PlanetaryAtmosphereReference:
        """获取行星大气参考数据"""
        return self.planetary_ref


# 便捷函数
def load_training_data(
    dataset: str = "synthetic",
    **kwargs
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """加载训练数据的便捷函数"""
    loader = UnifiedDatasetLoader()
    return loader.load_for_training(dataset, **kwargs)


def get_dataset_info() -> List[Dict[str, Any]]:
    """获取所有数据集信息"""
    loader = UnifiedDatasetLoader()
    datasets = loader.get_available_datasets()
    return [
        {
            "name": d.name,
            "path": str(d.path),
            "description": d.description,
            "n_samples": d.n_samples,
            "n_features": d.n_features,
            "labels": d.labels,
        }
        for d in datasets
    ]


if __name__ == "__main__":
    # 测试加载器
    print("=== 数据集加载器测试 ===\n")

    loader = UnifiedDatasetLoader()

    # 获取可用数据集
    print("可用数据集:")
    for info in loader.get_available_datasets():
        print(f"  - {info.name}: {info.n_samples} 样本, {info.n_features} 特征")
        print(f"    标签: {info.labels}")
        print()

    # 加载合成数据集
    print("加载合成数据集...")
    X, y, label_map = loader.load_for_training("synthetic")
    print(f"  X shape: {X.shape}")
    print(f"  y shape: {y.shape}")
    print(f"  标签映射: {label_map}")
    print()

    # 测试行星大气参考
    print("行星大气参考数据:")
    ref = loader.get_planetary_reference()
    for planet in ["mars", "venus", "comet", "earth_life", "background"]:
        info = ref.get_planet_info(planet)
        sv = ref.get_scientific_value(planet)
        print(f"  - {planet}: 科学价值 = {sv}")

    # 测试阈值分类
    print("\n阈值分类测试:")
    test_cases = [
        {"ch4_ppb": 0.5, "co2_percent": 95},  # Mars
        {"ph3_ppb": 1.0, "so2_ppm": 100, "h2s_ppb": 500},  # Venus
        {"ch4_ppb": 500, "h2s_ppb": 1500},  # Comet
        {"ch4_ppb": 1900, "co2_percent": 0.04},  # Earth life
    ]
    for case in test_cases:
        label, conf = ref.classify_by_thresholds(**case)
        print(f"  输入: {case}")
        print(f"  预测: {label} (置信度: {conf:.2f})")
        print()
