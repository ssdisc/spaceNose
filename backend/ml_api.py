"""
机器学习 API

提供：
- 场景分类样本写入/训练/预测
- 异常检测训练/预测（基于数据库历史）
- Year 1: 深度学习模型训练/预测/智能决策
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, SensorDataCRUD
from ml_service import ml_service


router = APIRouter(prefix="/api/ml", tags=["ml"])


class ScenarioSampleIn(BaseModel):
    label: str = Field(..., description="样本标签，例如：mars/venus/comet/custom")
    features: Dict[str, Any] = Field(..., description="特征向量：ch4/ph3/so2/h2s/co2/vocs")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="可选元信息")
    source: str = Field(default="frontend", description="来源标记")


class ScenarioPredictIn(BaseModel):
    features: Dict[str, Any] = Field(..., description="特征向量：ch4/ph3/so2/h2s/co2/vocs")


class AnomalyPredictIn(BaseModel):
    payload: Dict[str, Any] = Field(..., description="实时数据对象（adc/voltage/alcohol_ppm/co2_ppm...）")

class EnosePredictIn(BaseModel):
    features: Dict[str, Any] = Field(..., description="传感器阵列特征向量（例如 benzene/toluene/... 的 delta）")


class DLPredictIn(BaseModel):
    """深度学习预测输入"""
    features: Dict[str, Any] = Field(..., description="特征向量：ch4/ph3/so2/h2s/co2/vocs 或实时数据")


@router.get("/status")
async def ml_status():
    return {"success": True, "data": ml_service.status()}


@router.post("/scenario/sample")
async def add_scenario_sample(body: ScenarioSampleIn):
    result = ml_service.add_scenario_sample(
        label=body.label,
        features=body.features,
        meta=body.meta,
        source=body.source,
    )
    return {"success": True, "data": result}


@router.post("/scenario/train")
async def train_scenario_model(min_samples: int = Query(default=20, ge=5, le=5000)):
    result = await asyncio.to_thread(ml_service.train_scenario_model, min_samples)
    return {"success": bool(result.get("trained")), "data": result}


@router.post("/scenario/predict")
async def predict_scenario(body: ScenarioPredictIn):
    result = ml_service.predict_scenario(body.features)
    return {"success": bool(result.get("ok")), "data": result}


@router.post("/anomaly/train")
async def train_anomaly_model(
    limit: int = Query(default=1000, ge=50, le=20000),
    min_samples: int = Query(default=50, ge=10, le=5000),
    db: Session = Depends(get_db),
):
    rows = [item.to_dict() for item in SensorDataCRUD.get_latest(db, limit=limit)]
    result = await asyncio.to_thread(ml_service.train_anomaly_model, rows, min_samples)
    return {"success": bool(result.get("trained")), "data": result}


@router.post("/anomaly/predict")
async def predict_anomaly(body: AnomalyPredictIn):
    result = ml_service.predict_anomaly(body.payload)
    return {"success": bool(result.get("ok")), "data": result}


@router.post("/enose/train")
async def train_enose_model(
    dataset_path: Optional[str] = Query(default=None, description="CSV路径（默认使用仓库 datasets 目录下的示例数据集）"),
    label_mode: str = Query(default="delta_argmax", description="标签生成方式（当前仅支持 delta_argmax）"),
    min_samples: int = Query(default=20, ge=10, le=100000),
    min_class_samples: int = Query(default=2, ge=1, le=10000),
    test_size: float = Query(default=0.25, ge=0.1, le=0.5),
    random_state: int = Query(default=42, ge=0, le=10_000_000),
):
    result = await asyncio.to_thread(
        ml_service.train_enose_model,
        dataset_path,
        label_mode,
        min_samples,
        min_class_samples,
        test_size,
        random_state,
    )
    return {"success": bool(result.get("trained")), "data": result}


@router.get("/enose/sample")
async def sample_enose_dataset(
    dataset_path: Optional[str] = Query(default=None),
    label_mode: str = Query(default="delta_argmax"),
    index: Optional[int] = Query(default=None, ge=0),
):
    result = ml_service.sample_enose_dataset(dataset_path, label_mode, index)
    return {"success": bool(result.get("ok")), "data": result}


@router.post("/enose/predict")
async def predict_enose(body: EnosePredictIn):
    result = ml_service.predict_enose(body.features)
    return {"success": bool(result.get("ok")), "data": result}


# ============================================================================
# Year 1: Deep Learning Endpoints
# ============================================================================

@router.post("/dl/classifier/train")
async def train_dl_classifier(
    min_samples: int = Query(default=50, ge=10, le=10000),
    epochs: int = Query(default=100, ge=10, le=1000),
    batch_size: int = Query(default=16, ge=4, le=128),
    learning_rate: float = Query(default=0.001, ge=0.0001, le=0.1),
):
    """
    训练深度学习气体分类器 (1D-CNN + GRU)

    轻量化要求:
    - 模型大小 < 100KB
    - 推理时间 < 100ms
    """
    result = await asyncio.to_thread(
        ml_service.train_dl_classifier,
        min_samples,
        epochs,
        batch_size,
        learning_rate,
    )
    return {"success": bool(result.get("trained")), "data": result}


@router.post("/dl/autoencoder/train")
async def train_dl_autoencoder(
    limit: int = Query(default=1000, ge=50, le=20000),
    min_samples: int = Query(default=50, ge=10, le=5000),
    epochs: int = Query(default=100, ge=10, le=1000),
    batch_size: int = Query(default=16, ge=4, le=128),
    learning_rate: float = Query(default=0.001, ge=0.0001, le=0.1),
    db: Session = Depends(get_db),
):
    """
    训练深度学习自编码器 (Tiny Autoencoder) 用于异常检测

    轻量化要求:
    - 模型大小 < 100KB
    - 推理时间 < 100ms
    """
    rows = [item.to_dict() for item in SensorDataCRUD.get_latest(db, limit=limit)]
    result = await asyncio.to_thread(
        ml_service.train_dl_autoencoder,
        rows,
        min_samples,
        epochs,
        batch_size,
        learning_rate,
    )
    return {"success": bool(result.get("trained")), "data": result}


@router.post("/dl/predict")
async def dl_predict_with_decision(body: DLPredictIn):
    """
    深度学习推理 + 智能决策

    返回:
    - classification: 气体分类结果 (mars/venus/comet/earth_life/background)
    - anomaly_detection: 异常检测结果
    - decision: 智能决策 (compress/normal/priority/high_sample)
    - metrics: 推理性能指标
    """
    result = ml_service.predict_with_decision(body.features)
    return {"success": bool(result.get("ok")), "data": result}


@router.get("/dl/metrics")
async def get_dl_metrics():
    """
    获取深度学习模型的轻量化指标

    检查是否满足 Year 1 要求:
    - 模型大小 < 100KB
    - 推理时间 < 100ms
    """
    result = ml_service.get_dl_model_metrics()
    return {"success": result.get("available", False), "data": result}


@router.get("/dl/decision/explain")
async def explain_decision():
    """
    解释智能决策逻辑

    根据 PDF 要求:
    - compress: 背景气体，高压缩存储（90%压缩率）
    - normal: 正常存储
    - priority: 目标气体，高优先级下传
    - high_sample: 未知异常，触发高采样模式
    """
    return {
        "success": True,
        "data": {
            "decisions": {
                "compress": {
                    "description": "背景气体，高压缩存储（90%压缩率）",
                    "trigger": "识别为 background 且置信度 > 80%",
                    "action": "存储时应用高压缩率，降低下传优先级",
                },
                "normal": {
                    "description": "正常存储",
                    "trigger": "目标气体但置信度中等",
                    "action": "标准存储和下传流程",
                },
                "priority": {
                    "description": "目标气体检测，高优先级下传",
                    "trigger": "识别为 mars/venus/comet/earth_life 且置信度 > 70%",
                    "action": "立即标记为高优先级，优先下传",
                },
                "high_sample": {
                    "description": "未知异常，触发高采样模式",
                    "trigger": "检测到异常且分类置信度 < 60%",
                    "action": "触发高频采样模式，增加数据密度",
                },
            },
            "scientific_value": {
                "description": "科学价值评分 (0.0 - 1.0)",
                "weights": {
                    "mars": 0.95,
                    "venus": 0.90,
                    "comet": 0.85,
                    "earth_life": 0.80,
                    "background": 0.10,
                },
                "formula": "score = 0.5 * class_weight + 0.3 * anomaly_value + 0.2 * confidence",
            },
        },
    }


# ============================================================================
# Dataset Integration Endpoints
# ============================================================================

@router.get("/datasets")
async def list_datasets():
    """
    列出所有可用的数据集

    包括:
    - UCI Gas Sensor Array Dataset
    - Synthetic Biosignature Dataset
    - NASA PDS 行星大气参考数据
    """
    return {"success": True, "data": ml_service.status().get("datasets", {})}


@router.post("/dl/train/synthetic")
async def train_from_synthetic_dataset(
    epochs: int = Query(default=50, ge=10, le=500),
    batch_size: int = Query(default=32, ge=8, le=256),
    learning_rate: float = Query(default=0.001, ge=0.0001, le=0.1),
    test_size: float = Query(default=0.2, ge=0.1, le=0.4),
):
    """
    使用合成生物标志物数据集训练深度学习分类器

    该端点使用 datasets/synthetic/biosignature_dataset.json 中的数据
    训练行星气体分类器（mars/venus/comet/earth_life/background）

    轻量化要求:
    - 模型大小 < 100KB
    - 推理时间 < 100ms
    """
    import asyncio
    result = await asyncio.to_thread(
        ml_service.train_dl_from_synthetic_dataset,
        epochs,
        batch_size,
        learning_rate,
        test_size,
    )
    return {"success": bool(result.get("trained")), "data": result}


@router.post("/dl/train/uci")
async def train_from_uci_dataset(
    max_samples: int = Query(default=10000, ge=100, le=100000),
    epochs: int = Query(default=50, ge=10, le=500),
    batch_size: int = Query(default=32, ge=8, le=256),
    learning_rate: float = Query(default=0.001, ge=0.0001, le=0.1),
    test_size: float = Query(default=0.2, ge=0.1, le=0.4),
):
    """
    使用 UCI Gas Sensor Array 真实数据集训练深度学习分类器

    该端点使用真实传感器响应数据训练甲烷/CO 检测模型。
    数据来源: UCI Machine Learning Repository
    气体类型: Ethylene, Methane (CH4), CO
    传感器: 16 通道 (TGS-2600/2602/2610/2620)

    标签:
    - methane_high: 甲烷高浓度
    - methane_medium: 甲烷中浓度
    - co_high: 一氧化碳高浓度
    - co_medium: 一氧化碳中浓度
    - background: 背景
    """
    import asyncio
    result = await asyncio.to_thread(
        ml_service.train_dl_from_uci_dataset,
        max_samples,
        epochs,
        batch_size,
        learning_rate,
        test_size,
    )
    return {"success": bool(result.get("trained")), "data": result}
