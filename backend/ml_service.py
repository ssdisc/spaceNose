"""
机器学习服务（Year 1）

当前目标：
- 支持"场景/气味指纹"分类：从多气体向量（ch4/ph3/so2/h2s/co2/vocs）训练并预测。
- 支持异常检测：基于数据库历史训练 IsolationForest，并对实时数据输出异常分数。
- Year 1 新增：深度学习模型 (1D-CNN + GRU + Autoencoder)，智能决策引擎。

轻量化指标要求（星上部署）：
- 模型大小 < 100KB
- 推理时间 < 100ms
- 推理功耗 < 100mW

说明：
- 训练/推理都尽量轻量；训练通过 API 触发并在线程中执行，避免阻塞事件循环。
- 硬件端暂未上报多气体时，场景分类可先用前端模拟数据构建训练集演示。
"""

from __future__ import annotations

import csv
import json
import random
import threading
import time
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import numpy as np
    import joblib
    from sklearn.ensemble import IsolationForest
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    _ML_AVAILABLE = True
except Exception:  # pragma: no cover
    _ML_AVAILABLE = False

# Deep Learning imports
try:
    import torch
    from ml_models import (
        ModelConfig,
        GasClassifier1DCNN,
        GasClassifierGRU,
        HybridGasClassifier,
        TinyAutoencoder,
        IntelligentDecisionEngine,
        InferenceResult,
        get_model_size_kb,
        count_parameters,
        measure_inference_time,
        is_torch_available,
    )
    _DL_AVAILABLE = True
except Exception:
    _DL_AVAILABLE = False

# Dataset loader imports
try:
    from dataset_loader import (
        UnifiedDatasetLoader,
        SyntheticBiosignatureLoader,
        UCIGasSensorLoader,
        PlanetaryAtmosphereReference,
        load_training_data,
        get_dataset_info,
    )
    _DATASET_LOADER_AVAILABLE = True
except Exception:
    _DATASET_LOADER_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
MODEL_DIR = BASE_DIR / "ml_models"
DATA_DIR = BASE_DIR / "ml_data"

MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


SCENARIO_FEATURES = ["ch4", "ph3", "so2", "h2s", "co2", "vocs"]
ANOMALY_FEATURES = ["adc", "voltage", "alcohol_ppm", "co2_ppm"]

ENOSE_COMPOUNDS: List[Tuple[str, str]] = [
    ("benzene", "benzene"),
    ("heptane", "heptane"),
    ("toluene", "toluene"),
    ("isoprene", "isoprene"),
    ("methyl_pentane", "methyl-pentane"),
    ("decane", "decane"),
    ("pentane", "pentane"),
    ("octane", "octane"),
]
ENOSE_FEATURES = [key for key, _ in ENOSE_COMPOUNDS]
ENOSE_DEFAULT_DATASET_PATH = (
    REPO_ROOT
    / "datasets"
    / "hf"
    / "kordelfrance_Olfaction-Electrochemical-GCMS-Pairs"
    / "data"
    / "ec-gcms-inference-dataset.csv"
)


def _beijing_now_str() -> str:
    """返回北京时间字符串"""
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")


def _get_device() -> "torch.device":
    """获取训练设备，优先使用 GPU"""
    import torch
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")  # Apple Silicon
    return torch.device("cpu")


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
        if number != number:  # NaN
            return None
        return number
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False))
        f.write("\n")


@dataclass
class ModelInfo:
    enabled: bool
    trained_at: Optional[str] = None
    sample_count: int = 0
    features: Optional[List[str]] = None
    classes: Optional[List[str]] = None


class MlService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._scenario_model: Optional[Any] = None
        self._scenario_info = ModelInfo(enabled=False, features=SCENARIO_FEATURES)

        self._anomaly_model: Optional[Any] = None
        self._anomaly_info = ModelInfo(enabled=False, features=ANOMALY_FEATURES)

        self._enose_model: Optional[Any] = None
        self._enose_info = ModelInfo(enabled=False, features=ENOSE_FEATURES)

        # Year 1: Deep Learning models
        self._dl_config: Optional["ModelConfig"] = None
        self._dl_classifier: Optional[Any] = None
        self._dl_autoencoder: Optional[Any] = None
        self._dl_classifier_info = ModelInfo(enabled=False, features=SCENARIO_FEATURES)
        self._dl_autoencoder_info = ModelInfo(enabled=False, features=SCENARIO_FEATURES)
        self._decision_engine: Optional["IntelligentDecisionEngine"] = None

        # Time series buffer for deep learning
        self._ts_buffer: List[List[float]] = []
        self._ts_buffer_max_len: int = 16  # seq_length

        self._scenario_dataset_path = DATA_DIR / "scenario_samples.jsonl"
        self._scenario_model_path = MODEL_DIR / "scenario_classifier.joblib"
        self._anomaly_model_path = MODEL_DIR / "anomaly_isolation_forest.joblib"
        self._enose_model_path = MODEL_DIR / "enose_classifier.joblib"
        self._dl_classifier_path = MODEL_DIR / "dl_gas_classifier.pt"
        self._dl_autoencoder_path = MODEL_DIR / "dl_autoencoder.pt"

    def status(self) -> Dict[str, Any]:
        with self._lock:
            scenario_count = self.scenario_dataset_count()

            # Deep learning model stats
            dl_status = {
                "available": _DL_AVAILABLE,
                "classifier": {
                    "model": self._dl_classifier_info.__dict__,
                    "size_kb": None,
                    "inference_time_ms": None,
                },
                "autoencoder": {
                    "model": self._dl_autoencoder_info.__dict__,
                    "size_kb": None,
                },
            }

            if _DL_AVAILABLE and self._dl_classifier is not None:
                dl_status["classifier"]["size_kb"] = get_model_size_kb(self._dl_classifier)
            if _DL_AVAILABLE and self._dl_autoencoder is not None:
                dl_status["autoencoder"]["size_kb"] = get_model_size_kb(self._dl_autoencoder)

            # Dataset info
            dataset_status = {
                "loader_available": _DATASET_LOADER_AVAILABLE,
                "datasets": [],
            }
            if _DATASET_LOADER_AVAILABLE:
                try:
                    dataset_status["datasets"] = get_dataset_info()
                except Exception:
                    pass

            return {
                "ml_available": _ML_AVAILABLE,
                "dl_available": _DL_AVAILABLE,
                "scenario": {
                    "model": self._scenario_info.__dict__,
                    "dataset_count": scenario_count,
                    "dataset_path": str(self._scenario_dataset_path),
                },
                "anomaly": {"model": self._anomaly_info.__dict__},
                "enose": {
                    "model": self._enose_info.__dict__,
                    "dataset_path_default": str(ENOSE_DEFAULT_DATASET_PATH),
                    "dataset_exists_default": bool(ENOSE_DEFAULT_DATASET_PATH.exists()),
                },
                "deep_learning": dl_status,
                "datasets": dataset_status,
                "lightweight_metrics": {
                    "max_model_size_kb": 100,
                    "max_inference_time_ms": 100,
                    "target_deployment": "STM32H7/FPGA",
                },
            }

    def load_models(self) -> None:
        if not _ML_AVAILABLE:
            return
        with self._lock:
            self._scenario_model, self._scenario_info = self._load_model(
                self._scenario_model_path, default_features=SCENARIO_FEATURES
            )
            self._anomaly_model, self._anomaly_info = self._load_model(
                self._anomaly_model_path, default_features=ANOMALY_FEATURES
            )
            self._enose_model, self._enose_info = self._load_model(
                self._enose_model_path, default_features=ENOSE_FEATURES
            )

            # Load deep learning models
            self._load_dl_models()

    def scenario_dataset_count(self) -> int:
        if not self._scenario_dataset_path.exists():
            return 0
        try:
            with self._scenario_dataset_path.open("r", encoding="utf-8") as f:
                return sum(1 for _ in f if _.strip())
        except Exception:
            return 0

    def add_scenario_sample(
        self,
        label: str,
        features: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
    ) -> Dict[str, Any]:
        sample = {
            "label": str(label),
            "features": {k: _safe_float(features.get(k)) for k in SCENARIO_FEATURES},
            "meta": meta or {},
            "source": source,
            "ts": _beijing_now_str(),
        }
        with self._lock:
            _append_jsonl(self._scenario_dataset_path, sample)
            return {
                "saved": True,
                "dataset_count": self.scenario_dataset_count(),
            }

    def train_scenario_model(self, min_samples: int = 20) -> Dict[str, Any]:
        if not _ML_AVAILABLE:
            return {"trained": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}

        rows = _read_jsonl(self._scenario_dataset_path)
        if len(rows) < min_samples:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(rows)} 条，至少需要 {min_samples} 条",
            }

        x, y = self._build_scenario_xy(rows)
        if x.size == 0:
            return {"trained": False, "error": "样本解析失败：没有可用特征向量"}

        pipeline: Any = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=300,
                    ),
                ),
            ]
        )
        pipeline.fit(x, y)
        train_acc = float(pipeline.score(x, y))
        classes = [str(c) for c in getattr(pipeline.named_steps["clf"], "classes_", [])]

        payload = {
            "model": pipeline,
            "info": ModelInfo(
                enabled=True,
                trained_at=_beijing_now_str(),
                sample_count=int(len(y)),
                features=SCENARIO_FEATURES,
                classes=classes,
            ).__dict__,
        }
        joblib.dump(payload, self._scenario_model_path)

        with self._lock:
            self._scenario_model = pipeline
            self._scenario_info = ModelInfo(
                enabled=True,
                trained_at=payload["info"]["trained_at"],
                sample_count=payload["info"]["sample_count"],
                features=SCENARIO_FEATURES,
                classes=classes,
            )

        return {
            "trained": True,
            "train_accuracy": train_acc,
            "classes": classes,
            "sample_count": int(len(y)),
            "model_path": str(self._scenario_model_path),
        }

    def predict_scenario(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if not _ML_AVAILABLE:
            return {"ok": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}
        with self._lock:
            if not self._scenario_model:
                return {"ok": False, "error": "场景模型未训练"}
            x = self._vector_from_features(features, SCENARIO_FEATURES)
            proba = self._scenario_model.predict_proba(x)[0]
            classes = [str(c) for c in getattr(self._scenario_model.named_steps["clf"], "classes_", [])]
            if not classes:
                return {"ok": False, "error": "模型类别信息缺失"}
            best_idx = int(np.argmax(proba))
            return {
                "ok": True,
                "label": classes[best_idx],
                "confidence": float(proba[best_idx]),
                "probabilities": {classes[i]: float(proba[i]) for i in range(len(classes))},
            }

    def train_anomaly_model(self, rows: List[Dict[str, Any]], min_samples: int = 50) -> Dict[str, Any]:
        if not _ML_AVAILABLE:
            return {"trained": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}
        if len(rows) < min_samples:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(rows)} 条，至少需要 {min_samples} 条",
            }

        x = self._build_feature_matrix(rows, ANOMALY_FEATURES)
        if x.size == 0:
            return {"trained": False, "error": "样本解析失败：没有可用特征向量"}

        pipeline: Any = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "iso",
                    IsolationForest(
                        n_estimators=200,
                        random_state=42,
                        contamination="auto",
                    ),
                ),
            ]
        )
        pipeline.fit(x)

        payload = {
            "model": pipeline,
            "info": ModelInfo(
                enabled=True,
                trained_at=_beijing_now_str(),
                sample_count=int(x.shape[0]),
                features=ANOMALY_FEATURES,
            ).__dict__,
        }
        joblib.dump(payload, self._anomaly_model_path)

        with self._lock:
            self._anomaly_model = pipeline
            self._anomaly_info = ModelInfo(
                enabled=True,
                trained_at=payload["info"]["trained_at"],
                sample_count=payload["info"]["sample_count"],
                features=ANOMALY_FEATURES,
            )

        return {
            "trained": True,
            "sample_count": int(x.shape[0]),
            "model_path": str(self._anomaly_model_path),
        }

    def train_enose_model(
        self,
        dataset_path: Optional[str] = None,
        label_mode: str = "delta_argmax",
        min_samples: int = 20,
        min_class_samples: int = 2,
        test_size: float = 0.25,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        传感器阵列（Electronic Nose）分类训练。

        默认读取 ec-gcms-inference-dataset.csv，并使用 delta(stimulus-baseline) 的 argmax 生成标签：
        - label_mode=delta_argmax：取 8 个通道 delta 的最大者作为类别；若最大值<=0 归为 background。
        """
        if not _ML_AVAILABLE:
            return {"trained": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}

        if label_mode not in {"delta_argmax"}:
            return {"trained": False, "error": f"不支持的 label_mode: {label_mode}"}

        path = Path(dataset_path) if dataset_path else ENOSE_DEFAULT_DATASET_PATH
        if not path.exists():
            return {"trained": False, "error": f"数据集不存在: {path}"}

        rows = self._read_csv_rows(path)
        if len(rows) < min_samples:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(rows)} 条，至少需要 {min_samples} 条",
            }

        x_rows: List[List[Optional[float]]] = []
        y_rows: List[str] = []
        for row in rows:
            features = self._enose_features_from_row(row)
            label = self._enose_label_delta_argmax(features)
            x_rows.append([features.get(k) for k in ENOSE_FEATURES])
            y_rows.append(label)

        label_counts = Counter(y_rows)
        keep_labels = {k for k, v in label_counts.items() if v >= min_class_samples}
        if not keep_labels:
            return {"trained": False, "error": "过滤后无可训练类别（请降低 min_class_samples）"}

        x_f: List[List[Optional[float]]] = []
        y_f: List[str] = []
        for x, y in zip(x_rows, y_rows):
            if y not in keep_labels:
                continue
            x_f.append(x)
            y_f.append(y)

        if len(y_f) < min_samples:
            return {
                "trained": False,
                "error": f"过滤后样本不足：当前 {len(y_f)} 条，至少需要 {min_samples} 条",
            }

        x = np.array(x_f, dtype=float)
        y = np.array(y_f, dtype=str)

        try:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y,
                test_size=test_size,
                random_state=random_state,
                stratify=y,
            )
        except Exception:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y,
                test_size=test_size,
                random_state=random_state,
            )

        pipeline: Any = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        pipeline.fit(x_train, y_train)

        y_pred = pipeline.predict(x_test)
        test_accuracy = float(accuracy_score(y_test, y_pred))
        test_macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        classes = [str(c) for c in getattr(pipeline.named_steps["clf"], "classes_", [])]
        cm = confusion_matrix(y_test, y_pred, labels=classes).tolist() if classes else []

        payload = {
            "model": pipeline,
            "info": ModelInfo(
                enabled=True,
                trained_at=_beijing_now_str(),
                sample_count=int(len(y)),
                features=ENOSE_FEATURES,
                classes=classes,
            ).__dict__,
            "meta": {
                "label_mode": label_mode,
                "dataset_path": str(path),
                "label_counts": dict(label_counts),
                "kept_labels": sorted(keep_labels),
                "test_size": float(test_size),
                "random_state": int(random_state),
            },
            "metrics": {
                "test_accuracy": test_accuracy,
                "test_macro_f1": test_macro_f1,
                "confusion_matrix": cm,
                "confusion_matrix_labels": classes,
            },
        }
        joblib.dump(payload, self._enose_model_path)

        with self._lock:
            self._enose_model = pipeline
            self._enose_info = ModelInfo(
                enabled=True,
                trained_at=payload["info"]["trained_at"],
                sample_count=payload["info"]["sample_count"],
                features=ENOSE_FEATURES,
                classes=classes,
            )

        return {
            "trained": True,
            "sample_count": int(len(y)),
            "classes": classes,
            "label_counts": dict(label_counts),
            "kept_labels": sorted(keep_labels),
            "test_accuracy": test_accuracy,
            "test_macro_f1": test_macro_f1,
            "confusion_matrix": cm,
            "confusion_matrix_labels": classes,
            "model_path": str(self._enose_model_path),
        }

    def predict_enose(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if not _ML_AVAILABLE:
            return {"ok": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}
        with self._lock:
            if not self._enose_model:
                return {"ok": False, "error": "阵列分类模型未训练"}
            missing = [k for k in ENOSE_FEATURES if features.get(k) is None]
            if missing:
                return {"ok": False, "error": f"缺少特征: {', '.join(missing)}"}

            x = self._vector_from_features(features, ENOSE_FEATURES)
            proba = self._enose_model.predict_proba(x)[0]
            classes = [str(c) for c in getattr(self._enose_model.named_steps["clf"], "classes_", [])]
            if not classes:
                return {"ok": False, "error": "模型类别信息缺失"}
            best_idx = int(np.argmax(proba))
            return {
                "ok": True,
                "label": classes[best_idx],
                "confidence": float(proba[best_idx]),
                "probabilities": {classes[i]: float(proba[i]) for i in range(len(classes))},
            }

    def sample_enose_dataset(
        self,
        dataset_path: Optional[str] = None,
        label_mode: str = "delta_argmax",
        index: Optional[int] = None,
    ) -> Dict[str, Any]:
        if label_mode not in {"delta_argmax"}:
            return {"ok": False, "error": f"不支持的 label_mode: {label_mode}"}

        path = Path(dataset_path) if dataset_path else ENOSE_DEFAULT_DATASET_PATH
        if not path.exists():
            return {"ok": False, "error": f"数据集不存在: {path}"}

        rows = self._read_csv_rows(path)
        if not rows:
            return {"ok": False, "error": "数据集为空"}

        if index is None:
            index = random.randrange(0, len(rows))
        if index < 0 or index >= len(rows):
            return {"ok": False, "error": f"index 超出范围: 0~{len(rows) - 1}"}

        row = rows[index]
        features = self._enose_features_from_row(row)
        label = self._enose_label_delta_argmax(features)
        return {
            "ok": True,
            "index": int(index),
            "label": label,
            "features": features,
            "dataset_path": str(path),
        }

    def predict_anomaly(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not _ML_AVAILABLE:
            return {"ok": False, "error": "ML依赖未安装（numpy/scikit-learn/joblib）"}
        with self._lock:
            if not self._anomaly_model:
                return {"ok": False, "error": "异常模型未训练"}
            x = self._vector_from_features(payload, ANOMALY_FEATURES)
            pred = int(self._anomaly_model.predict(x)[0])  # 1=normal, -1=anomaly
            score = float(self._anomaly_model.decision_function(x)[0])
            return {
                "ok": True,
                "label": "anomaly" if pred == -1 else "normal",
                "score": score,
                "features": {k: _safe_float(payload.get(k)) for k in ANOMALY_FEATURES},
            }

    def enrich_realtime_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        在实时消息中附加 ml 字段，前端可直接展示。
        不修改数据库写入字段，避免对现有表结构产生额外要求。
        """
        ml: Dict[str, Any] = {}

        anomaly = self.predict_anomaly(payload)
        if anomaly.get("ok"):
            ml["anomaly"] = anomaly
        else:
            ml["anomaly"] = {"ok": False, "error": anomaly.get("error")}

        payload["ml"] = ml
        return payload

    def _build_scenario_xy(self, rows: List[Dict[str, Any]]) -> Tuple["np.ndarray", "np.ndarray"]:
        x_rows: List[List[Optional[float]]] = []
        y_rows: List[str] = []
        for row in rows:
            label = row.get("label")
            feat = row.get("features", {})
            if not label or not isinstance(feat, dict):
                continue
            vector = [_safe_float(feat.get(k)) for k in SCENARIO_FEATURES]
            x_rows.append(vector)
            y_rows.append(str(label))
        if not x_rows:
            return np.zeros((0, len(SCENARIO_FEATURES))), np.zeros((0,))
        return np.array(x_rows, dtype=float), np.array(y_rows, dtype=str)

    def _build_feature_matrix(self, rows: List[Dict[str, Any]], features: List[str]) -> "np.ndarray":
        x_rows: List[List[Optional[float]]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            x_rows.append([_safe_float(row.get(k)) for k in features])
        if not x_rows:
            return np.zeros((0, len(features)))
        return np.array(x_rows, dtype=float)

    def _vector_from_features(self, obj: Dict[str, Any], features: List[str]) -> "np.ndarray":
        return np.array([[ _safe_float(obj.get(k)) for k in features ]], dtype=float)

    def _read_csv_rows(self, path: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    def _enose_features_from_row(self, row: Dict[str, Any]) -> Dict[str, Optional[float]]:
        features: Dict[str, Optional[float]] = {}
        for key, compound in ENOSE_COMPOUNDS:
            baseline_key = f"baseline_{compound}"
            stimulus_key = f"stimulus_{compound}"
            baseline = _safe_float(row.get(baseline_key))
            stimulus = _safe_float(row.get(stimulus_key))
            if baseline is None or stimulus is None:
                features[key] = None
            else:
                features[key] = stimulus - baseline
        return features

    def _enose_label_delta_argmax(self, features: Dict[str, Optional[float]]) -> str:
        best_key = None
        best_val = None
        for key in ENOSE_FEATURES:
            value = features.get(key)
            if value is None:
                continue
            if best_key is None or value > best_val:
                best_key = key
                best_val = value
        if best_key is None or best_val is None or best_val <= 0:
            return "background"
        return best_key

    def _load_model(self, path: Path, default_features: List[str]) -> Tuple[Optional[Any], ModelInfo]:
        if not _ML_AVAILABLE or not path.exists():
            return None, ModelInfo(enabled=False, features=default_features)
        try:
            payload = joblib.load(path)
            model = payload.get("model")
            info_dict = payload.get("info") or {}
            info = ModelInfo(
                enabled=bool(info_dict.get("enabled")),
                trained_at=info_dict.get("trained_at"),
                sample_count=int(info_dict.get("sample_count") or 0),
                features=info_dict.get("features") or default_features,
                classes=info_dict.get("classes"),
            )
            return model, info
        except Exception:
            return None, ModelInfo(enabled=False, features=default_features)

    # =========================================================================
    # Year 1: Deep Learning Methods
    # =========================================================================

    def _load_dl_models(self) -> None:
        """加载深度学习模型"""
        if not _DL_AVAILABLE:
            return

        self._dl_config = ModelConfig()
        self._decision_engine = IntelligentDecisionEngine()

        # 加载分类器
        if self._dl_classifier_path.exists():
            try:
                checkpoint = torch.load(self._dl_classifier_path, map_location='cpu')
                self._dl_classifier = HybridGasClassifier(self._dl_config)
                self._dl_classifier.load_state_dict(checkpoint['model_state_dict'])
                self._dl_classifier.eval()
                self._dl_classifier_info = ModelInfo(
                    enabled=True,
                    trained_at=checkpoint.get('trained_at'),
                    sample_count=checkpoint.get('sample_count', 0),
                    features=SCENARIO_FEATURES,
                    classes=checkpoint.get('classes', IntelligentDecisionEngine.CLASS_NAMES),
                )
            except Exception:
                pass

        # 加载自编码器
        if self._dl_autoencoder_path.exists():
            try:
                checkpoint = torch.load(self._dl_autoencoder_path, map_location='cpu')
                self._dl_autoencoder = TinyAutoencoder(self._dl_config)
                self._dl_autoencoder.load_state_dict(checkpoint['model_state_dict'])
                self._dl_autoencoder.eval()
                self._dl_autoencoder_info = ModelInfo(
                    enabled=True,
                    trained_at=checkpoint.get('trained_at'),
                    sample_count=checkpoint.get('sample_count', 0),
                    features=SCENARIO_FEATURES,
                )
            except Exception:
                pass

    def train_dl_classifier(
        self,
        min_samples: int = 50,
        epochs: int = 100,
        batch_size: int = 16,
        learning_rate: float = 0.001,
    ) -> Dict[str, Any]:
        """
        训练深度学习气体分类器

        使用场景数据集训练 HybridGasClassifier (1D-CNN + GRU)
        """
        if not _DL_AVAILABLE:
            return {"trained": False, "error": "PyTorch未安装"}

        rows = _read_jsonl(self._scenario_dataset_path)
        if len(rows) < min_samples:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(rows)} 条，至少需要 {min_samples} 条",
            }

        # 准备数据
        x_list, y_list = [], []
        label_to_idx = {name: idx for idx, name in enumerate(IntelligentDecisionEngine.CLASS_NAMES)}

        for row in rows:
            label = str(row.get("label", "background")).lower()
            if label not in label_to_idx:
                label = "background"
            feat = row.get("features", {})
            vector = [_safe_float(feat.get(k)) or 0.0 for k in SCENARIO_FEATURES]
            x_list.append(vector)
            y_list.append(label_to_idx[label])

        # 创建时序数据（复制单个样本到seq_length维度用于演示）
        config = ModelConfig()
        x_seq = []
        for vec in x_list:
            seq = [vec] * config.seq_length
            x_seq.append(seq)

        x_tensor = torch.tensor(x_seq, dtype=torch.float32)
        y_tensor = torch.tensor(y_list, dtype=torch.long)

        # 获取设备（优先 GPU）
        device = _get_device()

        # 划分训练/验证集
        n_val = max(1, int(len(x_tensor) * 0.2))
        indices = torch.randperm(len(x_tensor))
        train_idx, val_idx = indices[n_val:], indices[:n_val]

        x_train, y_train = x_tensor[train_idx].to(device), y_tensor[train_idx].to(device)
        x_val, y_val = x_tensor[val_idx].to(device), y_tensor[val_idx].to(device)

        # 创建模型
        model = HybridGasClassifier(config).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = torch.nn.CrossEntropyLoss()

        # 训练
        model.train()
        best_val_acc = 0.0
        train_losses = []

        for epoch in range(epochs):
            # 随机打乱
            perm = torch.randperm(len(x_train))
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, len(x_train), batch_size):
                batch_idx = perm[i:i+batch_size]
                x_batch = x_train[batch_idx]
                y_batch = y_train[batch_idx]

                optimizer.zero_grad()
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            train_losses.append(epoch_loss / max(1, n_batches))

        # 验证
        model.eval()
        with torch.no_grad():
            val_logits = model(x_val)
            val_preds = torch.argmax(val_logits, dim=-1)
            val_acc = (val_preds == y_val).float().mean().item()

            train_logits = model(x_train)
            train_preds = torch.argmax(train_logits, dim=-1)
            train_acc = (train_preds == y_train).float().mean().item()

        # 检查轻量化指标（在 CPU 上测量）
        model.to("cpu")
        model_size_kb = get_model_size_kb(model)
        test_input = torch.randn(1, config.seq_length, config.n_features)
        inference_time_ms = measure_inference_time(model, test_input)

        # 保存模型
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'config': asdict(config),
            'trained_at': _beijing_now_str(),
            'device_used': str(device),
            'sample_count': len(rows),
            'classes': IntelligentDecisionEngine.CLASS_NAMES,
            'metrics': {
                'train_accuracy': train_acc,
                'val_accuracy': val_acc,
                'model_size_kb': model_size_kb,
                'inference_time_ms': inference_time_ms,
            },
        }
        torch.save(checkpoint, self._dl_classifier_path)

        # 更新实例
        with self._lock:
            self._dl_classifier = model
            self._dl_classifier_info = ModelInfo(
                enabled=True,
                trained_at=checkpoint['trained_at'],
                sample_count=len(rows),
                features=SCENARIO_FEATURES,
                classes=IntelligentDecisionEngine.CLASS_NAMES,
            )

        return {
            "trained": True,
            "train_accuracy": train_acc,
            "val_accuracy": val_acc,
            "sample_count": len(rows),
            "epochs": epochs,
            "model_size_kb": model_size_kb,
            "inference_time_ms": inference_time_ms,
            "lightweight_compliant": model_size_kb < 100 and inference_time_ms < 100,
            "model_path": str(self._dl_classifier_path),
            "device": str(device),
        }

    def train_dl_autoencoder(
        self,
        rows: List[Dict[str, Any]],
        min_samples: int = 50,
        epochs: int = 100,
        batch_size: int = 16,
        learning_rate: float = 0.001,
    ) -> Dict[str, Any]:
        """
        训练深度学习自编码器用于异常检测
        """
        if not _DL_AVAILABLE:
            return {"trained": False, "error": "PyTorch未安装"}

        if len(rows) < min_samples:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(rows)} 条，至少需要 {min_samples} 条",
            }

        # 准备数据
        config = ModelConfig()
        x_list = []
        for row in rows:
            vector = [_safe_float(row.get(k)) or 0.0 for k in ANOMALY_FEATURES]
            # 填充到 n_features
            while len(vector) < config.n_features:
                vector.append(0.0)
            vector = vector[:config.n_features]
            seq = [vector] * config.seq_length
            x_list.append(seq)

        x_tensor = torch.tensor(x_list, dtype=torch.float32)

        # 获取设备（优先 GPU）
        device = _get_device()
        x_tensor = x_tensor.to(device)

        # 创建模型
        model = TinyAutoencoder(config).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # 训练
        model.train()
        train_losses = []

        for epoch in range(epochs):
            perm = torch.randperm(len(x_tensor), device=device)
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, len(x_tensor), batch_size):
                batch_idx = perm[i:i+batch_size]
                x_batch = x_tensor[batch_idx]

                optimizer.zero_grad()
                reconstructed, _ = model(x_batch)
                loss = torch.nn.functional.mse_loss(reconstructed, x_batch)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            train_losses.append(epoch_loss / max(1, n_batches))

        # 计算异常阈值（使用训练数据的95分位数）
        model.eval()
        with torch.no_grad():
            scores = model.compute_anomaly_score(x_tensor)
            threshold = float(torch.quantile(scores, 0.95))
            model.threshold = threshold

        # 检查轻量化指标（在 CPU 上测量）
        model.to("cpu")
        model_size_kb = get_model_size_kb(model)
        test_input = torch.randn(1, config.seq_length, config.n_features)
        inference_time_ms = measure_inference_time(
            lambda x: model.compute_anomaly_score(x), test_input
        )

        # 保存模型
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'config': asdict(config),
            'threshold': threshold,
            'trained_at': _beijing_now_str(),
            'device_used': str(device),
            'sample_count': len(rows),
            'metrics': {
                'final_loss': train_losses[-1] if train_losses else 0,
                'model_size_kb': model_size_kb,
                'inference_time_ms': inference_time_ms,
            },
        }
        torch.save(checkpoint, self._dl_autoencoder_path)

        # 更新实例
        with self._lock:
            self._dl_autoencoder = model
            self._dl_autoencoder_info = ModelInfo(
                enabled=True,
                trained_at=checkpoint['trained_at'],
                sample_count=len(rows),
                features=ANOMALY_FEATURES,
            )

        return {
            "trained": True,
            "sample_count": len(rows),
            "epochs": epochs,
            "final_loss": train_losses[-1] if train_losses else 0,
            "threshold": threshold,
            "model_size_kb": model_size_kb,
            "inference_time_ms": inference_time_ms,
            "lightweight_compliant": model_size_kb < 100 and inference_time_ms < 100,
            "model_path": str(self._dl_autoencoder_path),
            "device": str(device),
        }

    def train_dl_from_synthetic_dataset(
        self,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """
        使用合成生物标志物数据集训练深度学习分类器

        该方法直接从 datasets/synthetic/biosignature_dataset.json 加载数据，
        训练行星气体分类器（mars/venus/comet/earth_life/background）
        """
        if not _DL_AVAILABLE:
            return {"trained": False, "error": "PyTorch未安装"}

        if not _DATASET_LOADER_AVAILABLE:
            return {"trained": False, "error": "数据集加载器不可用"}

        try:
            # 加载合成数据集
            X, y, label_map = load_training_data("synthetic")
        except FileNotFoundError as e:
            return {"trained": False, "error": f"数据集未找到: {e}"}
        except Exception as e:
            return {"trained": False, "error": f"加载数据集失败: {e}"}

        if len(X) < 100:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(X)} 条，至少需要 100 条",
            }

        # 准备数据
        config = ModelConfig()

        # 划分训练/验证集
        n_samples = len(X)
        n_val = int(n_samples * test_size)
        indices = np.random.permutation(n_samples)
        train_idx, val_idx = indices[n_val:], indices[:n_val]

        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        # 创建时序数据（每个样本复制 seq_length 次作为序列）
        def make_sequences(data: np.ndarray) -> np.ndarray:
            seq_list = []
            for vec in data:
                seq = np.tile(vec, (config.seq_length, 1))
                seq_list.append(seq)
            return np.array(seq_list)

        X_train_seq = make_sequences(X_train)
        X_val_seq = make_sequences(X_val)

        # 获取设备（优先 GPU）
        device = _get_device()

        x_train_tensor = torch.tensor(X_train_seq, dtype=torch.float32).to(device)
        y_train_tensor = torch.tensor(y_train, dtype=torch.long).to(device)
        x_val_tensor = torch.tensor(X_val_seq, dtype=torch.float32).to(device)
        y_val_tensor = torch.tensor(y_val, dtype=torch.long).to(device)

        # 创建模型
        model = HybridGasClassifier(config).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = torch.nn.CrossEntropyLoss()

        # 训练（逐 epoch 记录真实的训练/验证准确率，用于训练曲线）
        train_losses = []
        train_accuracies = []
        val_accuracies = []

        for epoch in range(epochs):
            model.train()
            perm = torch.randperm(len(x_train_tensor), device=device)
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, len(x_train_tensor), batch_size):
                batch_idx = perm[i:i+batch_size]
                x_batch = x_train_tensor[batch_idx]
                y_batch = y_train_tensor[batch_idx]

                optimizer.zero_grad()
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            train_losses.append(epoch_loss / max(1, n_batches))

            # 本 epoch 结束后，在完整训练集/验证集上评估真实准确率
            model.eval()
            with torch.no_grad():
                train_preds = torch.argmax(model(x_train_tensor), dim=-1)
                val_preds = torch.argmax(model(x_val_tensor), dim=-1)
                train_accuracies.append((train_preds == y_train_tensor).float().mean().item())
                val_accuracies.append((val_preds == y_val_tensor).float().mean().item())

        # 最终准确率即最后一个 epoch 的真实值
        train_acc = train_accuracies[-1] if train_accuracies else 0.0
        val_acc = val_accuracies[-1] if val_accuracies else 0.0

        # 反转标签映射
        idx_to_label = {v: k for k, v in label_map.items()}
        class_names = [str(idx_to_label.get(i, f"class_{i}")) for i in range(len(label_map))]

        # 检查轻量化指标（在 CPU 上测量）
        model.to("cpu")
        model_size_kb = get_model_size_kb(model)
        test_input = torch.randn(1, config.seq_length, config.n_features)
        inference_time_ms = measure_inference_time(model, test_input)

        # 保存模型
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'config': asdict(config),
            'trained_at': _beijing_now_str(),
            'device_used': str(device),
            'sample_count': len(X),
            'classes': class_names,
            'label_map': {str(k): int(v) for k, v in label_map.items()},
            'dataset': 'synthetic_biosignature',
            'metrics': {
                'train_accuracy': train_acc,
                'val_accuracy': val_acc,
                'model_size_kb': model_size_kb,
                'inference_time_ms': inference_time_ms,
            },
        }
        torch.save(checkpoint, self._dl_classifier_path)

        # 更新实例
        with self._lock:
            self._dl_classifier = model
            self._dl_classifier_info = ModelInfo(
                enabled=True,
                trained_at=checkpoint['trained_at'],
                sample_count=len(X),
                features=SCENARIO_FEATURES,
                classes=class_names,
            )

        # 训练历史（train_accuracies / val_accuracies）已在训练循环中逐 epoch 真实记录

        return {
            "trained": True,
            "dataset": "synthetic_biosignature",
            "train_accuracy": train_acc,
            "val_accuracy": val_acc,
            "sample_count": len(X),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "epochs": epochs,
            "classes": class_names,
            "label_distribution": {str(idx_to_label.get(i, f"class_{i}")): int((y == i).sum()) for i in range(len(label_map))},
            "model_size_kb": model_size_kb,
            "inference_time_ms": inference_time_ms,
            "lightweight_compliant": model_size_kb < 100 and inference_time_ms < 100,
            "model_path": str(self._dl_classifier_path),
            "device": str(device),
            "training_history": {
                "loss": train_losses,
                "train_accuracy": train_accuracies,
                "val_accuracy": val_accuracies,
            },
        }

    def train_dl_from_uci_dataset(
        self,
        max_samples: int = 10000,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """
        使用 UCI Gas Sensor Array 真实数据集训练深度学习分类器

        该方法使用真实传感器响应数据，训练甲烷/CO 检测模型。
        标签: methane_high, methane_medium, co_high, co_medium, background
        """
        if not _DL_AVAILABLE:
            return {"trained": False, "error": "PyTorch未安装"}

        if not _DATASET_LOADER_AVAILABLE:
            return {"trained": False, "error": "数据集加载器不可用"}

        try:
            from dataset_loader import UCIGasSensorLoader
            uci_loader = UCIGasSensorLoader()
            X, y, feature_names = uci_loader.load_combined(max_samples=max_samples)
        except FileNotFoundError as e:
            return {"trained": False, "error": f"UCI数据集未找到: {e}"}
        except Exception as e:
            return {"trained": False, "error": f"加载UCI数据集失败: {e}"}

        if len(X) < 100:
            return {
                "trained": False,
                "error": f"样本不足：当前 {len(X)} 条，至少需要 100 条",
            }

        # 编码标签
        unique_labels = sorted(set(y))
        label_map = {label: i for i, label in enumerate(unique_labels)}
        y_encoded = np.array([label_map[label] for label in y])

        # 标准化特征
        X_mean = X.mean(axis=0, keepdims=True)
        X_std = X.std(axis=0, keepdims=True) + 1e-8
        X_normalized = (X - X_mean) / X_std

        # 划分训练/验证集
        n_samples = len(X_normalized)
        n_val = int(n_samples * test_size)
        indices = np.random.permutation(n_samples)
        train_idx, val_idx = indices[n_val:], indices[:n_val]

        X_train, y_train = X_normalized[train_idx], y_encoded[train_idx]
        X_val, y_val = X_normalized[val_idx], y_encoded[val_idx]

        # UCI 有 16 个传感器，创建适配的模型配置
        uci_config = ModelConfig(
            n_features=16,  # UCI 有 16 个传感器
            seq_length=16,
            n_classes=len(unique_labels),
        )

        # 创建时序数据
        def make_sequences(data: np.ndarray, seq_len: int) -> np.ndarray:
            seq_list = []
            for vec in data:
                seq = np.tile(vec, (seq_len, 1))
                seq_list.append(seq)
            return np.array(seq_list)

        X_train_seq = make_sequences(X_train, uci_config.seq_length)
        X_val_seq = make_sequences(X_val, uci_config.seq_length)

        # 获取设备（优先 GPU）
        device = _get_device()

        x_train_tensor = torch.tensor(X_train_seq, dtype=torch.float32).to(device)
        y_train_tensor = torch.tensor(y_train, dtype=torch.long).to(device)
        x_val_tensor = torch.tensor(X_val_seq, dtype=torch.float32).to(device)
        y_val_tensor = torch.tensor(y_val, dtype=torch.long).to(device)

        # 创建模型
        model = HybridGasClassifier(uci_config).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = torch.nn.CrossEntropyLoss()

        # 训练
        model.train()
        for epoch in range(epochs):
            perm = torch.randperm(len(x_train_tensor), device=device)
            for i in range(0, len(x_train_tensor), batch_size):
                batch_idx = perm[i:i+batch_size]
                x_batch = x_train_tensor[batch_idx]
                y_batch = y_train_tensor[batch_idx]

                optimizer.zero_grad()
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()

        # 验证
        model.eval()
        with torch.no_grad():
            val_logits = model(x_val_tensor)
            val_preds = torch.argmax(val_logits, dim=-1)
            val_acc = (val_preds == y_val_tensor).float().mean().item()

            train_logits = model(x_train_tensor)
            train_preds = torch.argmax(train_logits, dim=-1)
            train_acc = (train_preds == y_train_tensor).float().mean().item()

        # 检查轻量化指标（在 CPU 上测量）
        model.to("cpu")
        model_size_kb = get_model_size_kb(model)
        test_input = torch.randn(1, uci_config.seq_length, uci_config.n_features)
        inference_time_ms = measure_inference_time(model, test_input)

        # 保存为 UCI 专用模型
        uci_model_path = MODEL_DIR / "dl_uci_classifier.pt"
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'config': asdict(uci_config),
            'trained_at': _beijing_now_str(),
            'device_used': str(device),
            'sample_count': len(X),
            'classes': unique_labels,
            'label_map': label_map,
            'normalization': {'mean': X_mean.tolist(), 'std': X_std.tolist()},
            'dataset': 'uci_gas_sensor',
            'metrics': {
                'train_accuracy': train_acc,
                'val_accuracy': val_acc,
                'model_size_kb': model_size_kb,
                'inference_time_ms': inference_time_ms,
            },
        }
        torch.save(checkpoint, uci_model_path)

        return {
            "trained": True,
            "dataset": "uci_gas_sensor",
            "data_type": "real_sensor_data",
            "train_accuracy": train_acc,
            "val_accuracy": val_acc,
            "sample_count": len(X),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "epochs": epochs,
            "classes": unique_labels,
            "feature_count": 16,
            "label_distribution": {label: int((y == label).sum()) for label in unique_labels},
            "model_size_kb": model_size_kb,
            "inference_time_ms": inference_time_ms,
            "lightweight_compliant": model_size_kb < 100 and inference_time_ms < 100,
            "model_path": str(uci_model_path),
            "device": str(device),
        }

    # 前端气体名 -> (传感器名, 灵敏度范围) 的映射
    # 训练数据集的特征顺序: MQ4_CH4, MQ136_H2S, MQ135_SO2, MQ135_CO2, MQ2_VOC, PH3_MOX
    _CONC_TO_SENSOR_MAP = [
        # (前端字段, 传感器名, 灵敏度范围 min, 灵敏度范围 max)
        ("ch4",  "MQ4_CH4",   200,   10000),
        ("h2s",  "MQ136_H2S", 1,     100),
        ("so2",  "MQ135_SO2", 10,    1000),
        ("co2",  "MQ135_CO2", 400,   10000),
        ("vocs", "MQ2_VOC",   100,   10000),
        ("ph3",  "PH3_MOX",   0.01,  10),
    ]

    def _concentration_to_sensor_response(self, features: Dict[str, Any]) -> List[float]:
        """
        将前端气体浓度 (ppm) 转换为模型训练时使用的传感器响应值 (0-1)

        使用与 dataset_generator.py 中完全一致的对数响应模型:
            response = (log10(conc) - log10(min)) / (log10(max) - log10(min))
            response = clip(response, 0, 1)

        同时修正特征顺序，输出按训练数据集的特征顺序排列:
            [MQ4_CH4, MQ136_H2S, MQ135_SO2, MQ135_CO2, MQ2_VOC, PH3_MOX]
        """
        import math
        vector = []
        for frontend_key, sensor_name, min_sens, max_sens in self._CONC_TO_SENSOR_MAP:
            conc = _safe_float(features.get(frontend_key)) or 0.0
            if conc <= 0:
                vector.append(0.0)
            else:
                log_conc = math.log10(max(conc, 1e-10))
                log_min = math.log10(max(min_sens, 1e-10))
                log_max = math.log10(max(max_sens, 1e-10))
                response = (log_conc - log_min) / (log_max - log_min)
                vector.append(max(0.0, min(1.0, response)))
        return vector

    def predict_with_decision(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用深度学习模型进行预测，并返回智能决策结果

        这是Year 1的核心功能：星上快速筛查 + 智能决策
        """
        if not _DL_AVAILABLE:
            return {"ok": False, "error": "PyTorch未安装"}

        start_time = time.perf_counter()

        # 准备输入：将前端气体浓度转换为训练时使用的传感器响应值
        config = self._dl_config or ModelConfig()
        vector = self._concentration_to_sensor_response(features)

        # 更新时序缓冲区
        self._ts_buffer.append(vector)
        if len(self._ts_buffer) > self._ts_buffer_max_len:
            self._ts_buffer = self._ts_buffer[-self._ts_buffer_max_len:]

        # 如果缓冲区不足，用当前值填充
        seq_data = list(self._ts_buffer)
        while len(seq_data) < config.seq_length:
            seq_data.insert(0, vector)

        x_tensor = torch.tensor([seq_data], dtype=torch.float32)


        # 分类预测
        class_idx = 4  # background
        class_name = "background"
        confidence = 0.0
        probabilities = {}

        if self._dl_classifier is not None:
            self._dl_classifier.eval()
            with torch.no_grad():
                logits = self._dl_classifier(x_tensor)
                probs = torch.softmax(logits, dim=-1)[0]
                class_idx = int(torch.argmax(probs))
                confidence = float(probs[class_idx])
                class_names = self._dl_classifier_info.classes if self._dl_classifier_info and self._dl_classifier_info.classes else IntelligentDecisionEngine.CLASS_NAMES
                probabilities = {class_names[i]: float(probs[i]) for i in range(len(class_names))}
                class_name = class_names[class_idx]

        # 异常检测
        is_anomaly = False
        anomaly_score = 0.0

        if self._dl_autoencoder is not None:
            self._dl_autoencoder.eval()
            with torch.no_grad():
                is_anomaly_tensor, scores = self._dl_autoencoder.detect_anomaly(x_tensor)
                is_anomaly = bool(is_anomaly_tensor[0])
                anomaly_score = float(scores[0])

        # 智能决策
        decision = "normal"
        scientific_value = 0.5

        if self._decision_engine is not None:
            scientific_value = self._decision_engine.compute_scientific_value(
                class_name, confidence, is_anomaly, anomaly_score
            )
            decision = self._decision_engine.make_decision(
                class_name, confidence, is_anomaly, scientific_value
            )

        inference_time_ms = (time.perf_counter() - start_time) * 1000

        return {
            "ok": True,
            "classification": {
                "class_idx": class_idx,
                "class_name": class_name,
                "confidence": confidence,
                "probabilities": probabilities,
            },
            "anomaly_detection": {
                "is_anomaly": is_anomaly,
                "score": anomaly_score,
                "threshold": self._dl_autoencoder.threshold if self._dl_autoencoder else 0.5,
            },
            "decision": {
                "action": decision,
                "scientific_value": scientific_value,
                "description": self._get_decision_description(decision),
            },
            "metrics": {
                "inference_time_ms": inference_time_ms,
                "buffer_length": len(self._ts_buffer),
                "lightweight_compliant": inference_time_ms < 100,
            },
        }

    def _get_decision_description(self, decision: str) -> str:
        """获取决策的描述"""
        descriptions = {
            "compress": "背景气体，高压缩存储（90%压缩率）",
            "normal": "正常存储",
            "priority": "目标气体检测，高优先级下传",
            "high_sample": "未知异常，触发高采样模式",
        }
        return descriptions.get(decision, "未知决策")

    def enrich_realtime_payload_v2(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Year 1增强版：在实时消息中附加深度学习推理结果和智能决策
        """
        ml: Dict[str, Any] = {}

        # 传统异常检测（兼容）
        anomaly = self.predict_anomaly(payload)
        if anomaly.get("ok"):
            ml["anomaly"] = anomaly
        else:
            ml["anomaly"] = {"ok": False, "error": anomaly.get("error")}

        # 深度学习推理 + 智能决策
        if _DL_AVAILABLE:
            dl_result = self.predict_with_decision(payload)
            if dl_result.get("ok"):
                ml["dl_classification"] = dl_result.get("classification")
                ml["dl_anomaly"] = dl_result.get("anomaly_detection")
                ml["decision"] = dl_result.get("decision")
                ml["inference_metrics"] = dl_result.get("metrics")

        payload["ml"] = ml
        return payload

    def get_dl_model_metrics(self) -> Dict[str, Any]:
        """获取深度学习模型的轻量化指标"""
        if not _DL_AVAILABLE:
            return {"available": False, "error": "PyTorch未安装"}

        metrics = {
            "available": True,
            "requirements": {
                "max_model_size_kb": 100,
                "max_inference_time_ms": 100,
            },
            "classifier": None,
            "autoencoder": None,
        }

        config = self._dl_config or ModelConfig()
        test_input = torch.randn(1, config.seq_length, config.n_features)
        classifier_checkpoint_metrics: Dict[str, Any] = {}
        if self._dl_classifier_path.exists():
            try:
                checkpoint = torch.load(self._dl_classifier_path, map_location="cpu")
                classifier_checkpoint_metrics = checkpoint.get("metrics") or {}
            except Exception:
                classifier_checkpoint_metrics = {}

        if self._dl_classifier is not None:
            if hasattr(self._dl_classifier, "state_dict") and hasattr(self._dl_classifier, "parameters"):
                size_kb = get_model_size_kb(self._dl_classifier)
                params = count_parameters(self._dl_classifier)
                inf_time = measure_inference_time(self._dl_classifier, test_input)
                metrics["classifier"] = {
                    "size_kb": size_kb,
                    "parameters": params,
                    "inference_time_ms": inf_time,
                    "train_accuracy": classifier_checkpoint_metrics.get("train_accuracy"),
                    "val_accuracy": classifier_checkpoint_metrics.get("val_accuracy"),
                    "size_compliant": size_kb < 100,
                    "time_compliant": inf_time < 100,
                }
            else:
                metrics["classifier"] = {
                    "error": f"invalid model object: {type(self._dl_classifier).__name__}"
                }

        if self._dl_autoencoder is not None:
            if hasattr(self._dl_autoencoder, "state_dict") and hasattr(self._dl_autoencoder, "parameters"):
                size_kb = get_model_size_kb(self._dl_autoencoder)
                params = count_parameters(self._dl_autoencoder)
                inf_time = measure_inference_time(self._dl_autoencoder, test_input)
                metrics["autoencoder"] = {
                    "size_kb": size_kb,
                    "parameters": params,
                    "inference_time_ms": inf_time,
                    "size_compliant": size_kb < 100,
                    "time_compliant": inf_time < 100,
                }
            else:
                inf_time = measure_inference_time(self._dl_autoencoder, test_input)
                metrics["autoencoder"] = {
                    "inference_time_ms": inf_time,
                    "error": f"invalid model object: {type(self._dl_autoencoder).__name__}"
                }

        return metrics


ml_service = MlService()
