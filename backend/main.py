from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import asyncio
import json
import base64
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# 导入数据库相关模块
from database import init_db, get_db, SessionLocal, SensorDataCRUD
from config import settings
from ml_api import router as ml_router
from ml_service import ml_service
from pus import (
    DEFAULT_APID,
    PUS1_ACCEPTANCE_FAILURE,
    PUS1_ACCEPTANCE_SUCCESS,
    PUS1_COMPLETION_FAILURE,
    PUS1_COMPLETION_SUCCESS,
    PUS3_HK_REPORT,
    PUS_SERVICE_EVENT_REPORTING,
    PUS_SERVICE_HOUSEKEEPING,
    PUS_SERVICE_TC_VERIFICATION,
    make_tc_set_rate,
    make_tc_tm_ack,
    parse_primary_header,
    parse_pus_packet,
    looks_like_primary_header,
    unpack_tc_verification_user_data,
 )

app = FastAPI()

# 允许跨域请求：前端开发服务器(:8080)与后端API(:8000)端口不同，
# 属于不同源，浏览器会拦截 fetch 请求。开放 CORS 以便前端读取数据库历史数据。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ml_router)

# 静态文件目录，指向Vue项目的dist目录
static_folder = os.path.join(os.path.dirname(__file__), "..", "web", "dist")

# 挂载静态文件
static_dirs = ["assets", "css", "js", "img"]
for static_dir in static_dirs:
    path = os.path.join(static_folder, static_dir)
    if os.path.exists(path) and os.path.isdir(path):
        app.mount(f"/{static_dir}", StaticFiles(directory=path), name=static_dir)

# favicon.ico 路由
@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join(static_folder, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return FileResponse(status_code=404)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✓ WebSocket客户端已连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"✗ WebSocket客户端已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """广播消息给所有连接的客户端"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"发送消息失败: {e}")

manager = ConnectionManager()

# TCP服务器配置（从配置文件读取，兼容旧的UDP环境变量）
TCP_HOST = settings.TCP_HOST
TCP_PORT = settings.TCP_PORT

# ==================== 自适应采样控制 ====================
# 活跃的TCP连接（硬件设备）
active_tcp_writers: Dict[str, asyncio.StreamWriter] = {}
# 设备是否支持 ECSS PUS（收到过合法 PUS 包即视为支持）
device_supports_pus: Dict[str, bool] = {}
# 下行 PUS Telecommand 等待 Verification（Service 1）
pending_downlink_pus_tcs: Dict[str, Dict[Tuple[int, int], Dict[str, Any]]] = {}
_downlink_tc_seq: int = 1

# 事件下传缓存（地面侧最近事件，便于调试/展示；不入库）
MAX_EVENTS_PER_DEVICE = 200
recent_link_events: Dict[str, List[Dict[str, Any]]] = {}
# 当前采样率（毫秒）
current_sampling_rate_ms = 5000
# 高采样模式的采样率
HIGH_SAMPLE_RATE_MS = 1000
# 常规采样率
NORMAL_SAMPLE_RATE_MS = 5000
# 上次决策状态（避免重复发送指令）
last_decision_state: Dict[str, str] = {}

async def send_sampling_rate_to_device(writer: asyncio.StreamWriter, rate_ms: int, peer_ip: str = "unknown"):
    """向硬件发送采样率指令（ECSS PUS 协议）"""
    try:
        global _downlink_tc_seq
        seq_count = _downlink_tc_seq & 0x3FFF
        _downlink_tc_seq = (seq_count + 1) & 0x3FFF

        pkt = make_tc_set_rate(rate_ms=int(rate_ms), apid=DEFAULT_APID, seq_count=seq_count)
        primary = parse_primary_header(pkt[:6])
        tc_packet_id = (1 << 12) | (1 << 11) | (primary.apid & 0x07FF)
        tc_seq_ctrl = ((primary.seq_flags & 0x3) << 14) | (primary.seq_count & 0x3FFF)

        pending_downlink_pus_tcs.setdefault(peer_ip, {})[(tc_packet_id, tc_seq_ctrl)] = {
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cmd": "set_rate",
            "rate_ms": int(rate_ms),
            "accepted": False,
        }

        writer.write(pkt)
        await writer.drain()
        print(f"✓(PUS) 向设备 {peer_ip} 发送采样率指令: {rate_ms}ms seq={seq_count}")
        return True
    except Exception as e:
        print(f"⚠ 发送采样率指令失败 {peer_ip}: {e}")
        return False

async def trigger_high_sampling(peer_ip: str):
    """触发高采样模式"""
    global current_sampling_rate_ms
    if peer_ip in active_tcp_writers:
        current_sampling_rate_ms = HIGH_SAMPLE_RATE_MS
        await send_sampling_rate_to_device(
            active_tcp_writers[peer_ip],
            HIGH_SAMPLE_RATE_MS,
            peer_ip
        )
        print(f"⚡ 触发高采样模式: {peer_ip}")

async def restore_normal_sampling(peer_ip: str):
    """恢复常规采样模式"""
    global current_sampling_rate_ms
    if peer_ip in active_tcp_writers:
        current_sampling_rate_ms = NORMAL_SAMPLE_RATE_MS
        await send_sampling_rate_to_device(
            active_tcp_writers[peer_ip],
            NORMAL_SAMPLE_RATE_MS,
            peer_ip
        )
        print(f"◐ 恢复常规采样模式: {peer_ip}")

# 存储最新的传感器数据
latest_data = {
    "counter": 0,
    "adc": 0,
    "voltage": 0.0,
    "mq3_adc": 0,
    "mq3_voltage": 0.0,
    "alcohol_ppm": 0.0,
    "co2_ppm": None,
    "sensor_status": 0,
    "timestamp": ""
}

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _record_pus_event(peer_id: str, pkt, payload: Any) -> None:
    evt = {
        "peer_id": peer_id,
        "received_at": _now_str(),
        "apid": getattr(pkt.primary, "apid", None),
        "seq": getattr(pkt.primary, "seq_count", None),
        "svc": getattr(pkt, "service_type", None),
        "sub": getattr(pkt, "service_subtype", None),
        "payload": payload,
    }
    bucket = recent_link_events.setdefault(peer_id, [])
    bucket.append(evt)
    if len(bucket) > MAX_EVENTS_PER_DEVICE:
        del bucket[0: max(0, len(bucket) - MAX_EVENTS_PER_DEVICE)]


def _tm_packet_id_and_seq_ctrl(apid: int, seq_flags: int, seq_count: int) -> Tuple[int, int]:
    packet_id = (0 << 13) | (0 << 12) | (1 << 11) | (apid & 0x07FF)
    seq_ctrl = ((seq_flags & 0x3) << 14) | (seq_count & 0x3FFF)
    return packet_id, seq_ctrl


def _tc_packet_id_and_seq_ctrl(apid: int, seq_flags: int, seq_count: int) -> Tuple[int, int]:
    packet_id = (0 << 13) | (1 << 12) | (1 << 11) | (apid & 0x07FF)
    seq_ctrl = ((seq_flags & 0x3) << 14) | (seq_count & 0x3FFF)
    return packet_id, seq_ctrl


def _alloc_tc_seq_count() -> int:
    global _downlink_tc_seq
    seq_count = _downlink_tc_seq & 0x3FFF
    _downlink_tc_seq = (seq_count + 1) & 0x3FFF
    return seq_count


async def _handle_pus_packet(
    peer_id: str, packet: bytes, writer: Optional[asyncio.StreamWriter]
) -> Optional[bytes]:
    global _downlink_tc_seq

    try:
        pkt = parse_pus_packet(packet)
    except Exception as e:
        print(f"✗ PUS解析失败 {peer_id}: {e}")
        return None

    device_supports_pus[peer_id] = True

    # TM: Telemetry
    if pkt.is_tm:
        # Service 1: TC Verification
        if pkt.service_type == PUS_SERVICE_TC_VERIFICATION:
            ref = unpack_tc_verification_user_data(pkt.user_data)
            if ref is None:
                return None
            tc_key = ref  # (packet_id, seq_ctrl)
            pending = pending_downlink_pus_tcs.get(peer_id, {})
            if tc_key not in pending:
                return None

            if pkt.service_subtype in (PUS1_ACCEPTANCE_SUCCESS, PUS1_ACCEPTANCE_FAILURE):
                pending[tc_key]["accepted"] = pkt.service_subtype == PUS1_ACCEPTANCE_SUCCESS
                pending[tc_key]["accepted_at"] = _now_str()
                print(f"✓(PUS) TC验收回报: {peer_id} key={tc_key} ok={pending[tc_key]['accepted']}")
                return None

            if pkt.service_subtype in (PUS1_COMPLETION_SUCCESS, PUS1_COMPLETION_FAILURE):
                ok = pkt.service_subtype == PUS1_COMPLETION_SUCCESS
                pending.pop(tc_key, None)
                print(f"✓(PUS) TC完成回报: {peer_id} key={tc_key} ok={ok}")
                return None

            return None

        # Service 5: Event reporting（事件下传）
        if pkt.service_type == PUS_SERVICE_EVENT_REPORTING:
            try:
                payload = json.loads(pkt.user_data.decode("utf-8"))
            except Exception:
                payload = {"raw": pkt.user_data.decode("utf-8", errors="replace")}

            _record_pus_event(peer_id, pkt, payload)
            print(f"✓(PUS) 收到事件: {peer_id} seq={pkt.primary.seq_count} payload={payload}")

            # 事件可靠下传：收到事件后回 TM-ACK（任务自定义服务 129/2）
            seq_count = _alloc_tc_seq_count()
            tm_pid, tm_sc = _tm_packet_id_and_seq_ctrl(pkt.primary.apid, pkt.primary.seq_flags, pkt.primary.seq_count)
            ack_tc = make_tc_tm_ack(
                tm_packet_id=tm_pid,
                tm_seq_ctrl=tm_sc,
                apid=DEFAULT_APID,
                seq_count=seq_count,
            )
            if writer is not None:
                writer.write(ack_tc)
                await writer.drain()
                return None
            return ack_tc

        # Service 3: Housekeeping（周期遥测）
        if pkt.service_type == PUS_SERVICE_HOUSEKEEPING and pkt.service_subtype == PUS3_HK_REPORT:
            try:
                payload = json.loads(pkt.user_data.decode("utf-8"))
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                payload["_link"] = {"pus": {"apid": pkt.primary.apid, "seq": pkt.primary.seq_count, "svc": pkt.service_type, "sub": pkt.service_subtype}}
                await _process_sensor_sample(peer_id, payload)
            return None

        return None

    # TC: Telecommand（通常不会从设备上行收到）
    return None


async def _process_sensor_sample(peer_ip: str, sensor_data: Dict[str, Any]) -> None:
    sensor_data["timestamp"] = _now_str()
    sensor_data["co2_ppm"] = sensor_data.get("co2_ppm")
    sensor_data = ml_service.enrich_realtime_payload(sensor_data)

    global latest_data
    latest_data = sensor_data

    print(f"✓ 收到数据: {sensor_data}")

    # ========== 自适应采样：根据ML决策自动调整采样率 ==========
    ml_result = sensor_data.get("ml", {})
    decision_info = ml_result.get("decision", {})
    decision_action = decision_info.get("action", "normal")

    # 只在决策状态变化时发送指令（避免重复发送）
    if decision_action != last_decision_state.get(peer_ip):
        if decision_action == "high_sample":
            await trigger_high_sampling(peer_ip)
        elif decision_action in ("compress", "normal") and last_decision_state.get(peer_ip) == "high_sample":
            await restore_normal_sampling(peer_ip)
        last_decision_state[peer_ip] = decision_action

    try:
        db = SessionLocal()
        SensorDataCRUD.create(
            db=db,
            counter=sensor_data.get("counter", 0),
            adc=sensor_data.get("adc", 0),
            voltage=sensor_data.get("voltage", 0.0),
            mq3_adc=sensor_data.get("mq3_adc"),
            mq3_voltage=sensor_data.get("mq3_voltage"),
            alcohol_ppm=sensor_data.get("alcohol_ppm"),
            co2_ppm=sensor_data.get("co2_ppm"),
            sensor_status=sensor_data.get("sensor_status"),
            source_ip=peer_ip,
        )
        db.close()
    except Exception as db_error:
        print(f"⚠ 数据库保存失败: {db_error}")

    await manager.broadcast(json.dumps(sensor_data))


async def handle_tcp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """处理单个TCP客户端（ECSS PUS 二进制协议）"""
    addr = writer.get_extra_info("peername")
    peer_ip = addr[0] if addr else "unknown"
    print(f"✓ TCP客户端连接: {peer_ip}")

    # 保存writer引用，支持双向通信
    active_tcp_writers[peer_ip] = writer
    last_decision_state[peer_ip] = "normal"

    rx_buf = bytearray()
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break

            rx_buf.extend(data)

            while True:
                # 解析 PUS 包（必须满足：primary header 合法 + secondary header PUS version 匹配）
                if len(rx_buf) >= 13 and looks_like_primary_header(rx_buf[:6]) and ((rx_buf[6] >> 4) & 0xF) == 2:
                    try:
                        primary = parse_primary_header(rx_buf[:6])
                        total_len = primary.total_len
                    except Exception:
                        break

                    if len(rx_buf) < total_len:
                        break

                    packet = bytes(rx_buf[:total_len])
                    del rx_buf[:total_len]
                    await _handle_pus_packet(peer_ip, packet, writer)
                    continue

                # 防御：异常情况下避免缓冲区无限增长
                if len(rx_buf) > 8192:
                    print(f"⚠ RX缓冲区过大({len(rx_buf)})，丢弃部分数据: {peer_ip}")
                    del rx_buf[: len(rx_buf) - 1024]
                break
    except asyncio.CancelledError:
        pass
    finally:
        # 清理连接引用
        if peer_ip in active_tcp_writers:
            del active_tcp_writers[peer_ip]
        if peer_ip in last_decision_state:
            del last_decision_state[peer_ip]
        writer.close()
        await writer.wait_closed()
        print(f"✗ TCP客户端断开: {peer_ip}")


async def tcp_server():
    """TCP服务器，接收来自ESP8266的数据"""
    server = await asyncio.start_server(handle_tcp_client, TCP_HOST, TCP_PORT)
    print(f"✓ TCP服务器启动在 {TCP_HOST}:{TCP_PORT}")
    async with server:
        await server.serve_forever()


class PusIngestIn(BaseModel):
    peer_id: str = Field(..., min_length=1, description="设备标识，例如 192.168.1.10 或 lora:dev1")
    packet_b64: str = Field(..., min_length=1, description="原始 PUS 包（二进制）base64 编码")


@app.post("/api/pus/ingest")
async def ingest_pus_packet(body: PusIngestIn):
    """
    PUS 网关入口（适用于 LoRa/串口网关转发）

    网关将收到的二进制 PUS 包 base64 编码后通过 HTTP 转发到此接口；若需要回包（例如事件 TM-ACK），
    会在响应中返回 `ack_packet_b64`，网关再通过原链路回传给设备。
    """
    try:
        packet = base64.b64decode(body.packet_b64, validate=True)
    except Exception as e:
        return {"success": False, "error": f"base64 解码失败: {e}"}

    ack = await _handle_pus_packet(body.peer_id, packet, writer=None)
    return {
        "success": True,
        "ack_packet_b64": base64.b64encode(ack).decode("ascii") if ack else None,
    }


class PusSetRateIn(BaseModel):
    peer_id: str = Field(..., min_length=1, description="目标设备标识（TCP设备用IP；LoRa可用自定义ID）")
    rate_ms: int = Field(..., ge=100, le=60000, description="采样率（毫秒）")
    send_if_connected: bool = Field(default=True, description="若目标为TCP直连设备，是否直接下发（默认True）")


@app.post("/api/pus/set_rate")
async def pus_set_rate(body: PusSetRateIn):
    """
    生成/下发 PUS Telecommand（任务自定义服务 129/1）：设置采样率。

    - TCP直连且设备已表现出 PUS 能力：可直接下发
    - LoRa网关：可取回 `packet_b64` 并通过 LoRa 发射；设备回包可走 `/api/pus/ingest`
    """
    seq_count = _alloc_tc_seq_count()
    pkt = make_tc_set_rate(rate_ms=int(body.rate_ms), apid=DEFAULT_APID, seq_count=seq_count)
    primary = parse_primary_header(pkt[:6])
    tc_pid, tc_sc = _tc_packet_id_and_seq_ctrl(primary.apid, primary.seq_flags, primary.seq_count)

    pending_downlink_pus_tcs.setdefault(body.peer_id, {})[(tc_pid, tc_sc)] = {
        "sent_at": _now_str(),
        "cmd": "set_rate",
        "rate_ms": int(body.rate_ms),
        "accepted": False,
    }

    sent = False
    if body.send_if_connected and body.peer_id in active_tcp_writers and device_supports_pus.get(body.peer_id):
        writer = active_tcp_writers[body.peer_id]
        try:
            writer.write(pkt)
            await writer.drain()
            sent = True
        except Exception as e:
            return {"success": False, "error": f"TCP下发失败: {e}"}

    return {
        "success": True,
        "seq": seq_count,
        "packet_b64": base64.b64encode(pkt).decode("ascii"),
        "sent": sent,
        "tc_key": f"{tc_pid:04X}:{tc_sc:04X}",
    }


@app.get("/api/pus/events")
async def get_pus_events(
    peer_id: Optional[str] = Query(default=None, description="过滤指定设备（可选）"),
    limit: int = Query(default=50, ge=1, le=500, description="返回条数"),
):
    """获取最近 PUS 事件下传记录（内存缓存，用于调试链路）"""
    if peer_id:
        events = list(recent_link_events.get(peer_id, []))
    else:
        events = []
        for _, bucket in recent_link_events.items():
            events.extend(bucket)
        events.sort(key=lambda x: x.get("received_at") or "", reverse=True)

    return {"success": True, "count": min(len(events), limit), "data": events[:limit]}


@app.on_event("startup")
async def startup_event():
    """启动TCP服务器和初始化数据库"""
    # 初始化数据库
    print("========================================")
    print("  星际嗅探者 - 后端服务器启动")
    print("========================================")
    
    if init_db():
        print(f"✓ 数据库连接成功: {settings.DB_NAME}")
    else:
        print("⚠ 数据库连接失败，请检查配置")

    ml_service.load_models()
    ml_status = ml_service.status()
    print(f"✓ ML模块: available={ml_status.get('ml_available')}, "
          f"scenario_model={ml_status.get('scenario', {}).get('model', {}).get('enabled')}, "
          f"anomaly_model={ml_status.get('anomaly', {}).get('model', {}).get('enabled')}")
    
    # 启动TCP服务器
    asyncio.create_task(tcp_server())
    
    print(f"✓ HTTP服务: http://127.0.0.1:{settings.SERVER_PORT}")
    print(f"✓ TCP服务: {TCP_HOST}:{TCP_PORT}")
    print(f"✓ WebSocket: ws://127.0.0.1:{settings.SERVER_PORT}/ws")
    print("========================================")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时推送数据到前端"""
    await manager.connect(websocket)
    
    # 发送最新数据给刚连接的客户端
    if latest_data["counter"] > 0:
        await websocket.send_text(json.dumps(latest_data))
    
    try:
        while True:
            # 保持连接，接收客户端消息（如果有）
            data = await websocket.receive_text()
            # 可以在这里处理客户端发来的消息
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/latest")
async def get_latest_data():
    """获取最新的传感器数据（内存中的）"""
    return latest_data

# ==================== 自适应采样API接口 ====================

@app.get("/api/sampling/rate")
async def get_sampling_rate():
    """获取当前采样率设置"""
    return {
        "success": True,
        "rate_ms": current_sampling_rate_ms,
        "mode": "high_sample" if current_sampling_rate_ms == HIGH_SAMPLE_RATE_MS else "normal",
        "connected_devices": list(active_tcp_writers.keys())
    }

@app.post("/api/sampling/rate")
async def set_sampling_rate(rate_ms: int = Query(ge=100, le=60000, description="采样率（毫秒）")):
    """手动设置硬件采样率 (100ms - 60s)"""
    global current_sampling_rate_ms
    current_sampling_rate_ms = rate_ms

    # 向所有连接的硬件发送指令
    results = {}
    for ip, writer in active_tcp_writers.items():
        success = await send_sampling_rate_to_device(writer, rate_ms, ip)
        results[ip] = "success" if success else "failed"

    return {
        "success": True,
        "rate_ms": rate_ms,
        "devices_updated": results
    }

@app.post("/api/sampling/high")
async def trigger_high_sample_mode():
    """手动触发高采样模式"""
    global current_sampling_rate_ms
    current_sampling_rate_ms = HIGH_SAMPLE_RATE_MS

    results = {}
    for ip, writer in active_tcp_writers.items():
        success = await send_sampling_rate_to_device(writer, HIGH_SAMPLE_RATE_MS, ip)
        results[ip] = "success" if success else "failed"

    return {
        "success": True,
        "mode": "high_sample",
        "rate_ms": HIGH_SAMPLE_RATE_MS,
        "devices_updated": results
    }

@app.post("/api/sampling/normal")
async def restore_normal_sample_mode():
    """恢复常规采样模式"""
    global current_sampling_rate_ms
    current_sampling_rate_ms = NORMAL_SAMPLE_RATE_MS

    results = {}
    for ip, writer in active_tcp_writers.items():
        success = await send_sampling_rate_to_device(writer, NORMAL_SAMPLE_RATE_MS, ip)
        results[ip] = "success" if success else "failed"

    return {
        "success": True,
        "mode": "normal",
        "rate_ms": NORMAL_SAMPLE_RATE_MS,
        "devices_updated": results
    }

@app.get("/api/devices")
async def get_connected_devices():
    """获取当前连接的硬件设备列表"""
    return {
        "success": True,
        "count": len(active_tcp_writers),
        "devices": [
            {
                "ip": ip,
                "last_decision": last_decision_state.get(ip, "unknown")
            }
            for ip in active_tcp_writers.keys()
        ]
    }

# ==================== 数据库API接口 ====================

@app.get("/api/data/recent")
async def get_recent_data(
    limit: int = Query(default=100, ge=1, le=1000, description="返回的数据条数"),
    db: Session = Depends(get_db)
):
    """获取最近的N条数据库记录"""
    data_list = SensorDataCRUD.get_latest(db, limit=limit)
    return {
        "success": True,
        "count": len(data_list),
        "data": [item.to_dict() for item in data_list]
    }

@app.get("/api/data/hours")
async def get_recent_hours_data(
    hours: int = Query(default=1, ge=1, le=24, description="获取最近N小时的数据"),
    db: Session = Depends(get_db)
):
    """获取最近N小时的数据"""
    data_list = SensorDataCRUD.get_recent_hours(db, hours=hours)
    return {
        "success": True,
        "count": len(data_list),
        "hours": hours,
        "data": [item.to_dict() for item in data_list]
    }

@app.get("/api/data/range")
async def get_data_by_range(
    start: str = Query(..., description="开始时间，格式: YYYY-MM-DD HH:MM:SS"),
    end: str = Query(..., description="结束时间，格式: YYYY-MM-DD HH:MM:SS"),
    db: Session = Depends(get_db)
):
    """根据时间范围获取数据"""
    try:
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        data_list = SensorDataCRUD.get_by_time_range(db, start_time, end_time)
        return {
            "success": True,
            "count": len(data_list),
            "start_time": start,
            "end_time": end,
            "data": [item.to_dict() for item in data_list]
        }
    except ValueError as e:
        return {
            "success": False,
            "error": f"时间格式错误: {str(e)}"
        }

@app.get("/api/data/{data_id}")
async def get_data_by_id(
    data_id: int,
    db: Session = Depends(get_db)
):
    """根据ID获取单条数据"""
    data = SensorDataCRUD.get_by_id(db, data_id)
    if data:
        return {
            "success": True,
            "data": data.to_dict()
        }
    else:
        return {
            "success": False,
            "error": "数据不存在"
        }

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """获取数据统计信息"""
    total_count = SensorDataCRUD.get_count(db)
    recent_data = SensorDataCRUD.get_latest(db, limit=1)
    
    return {
        "success": True,
        "total_records": total_count,
        "latest_record": recent_data[0].to_dict() if recent_data else None,
        "database": settings.DB_NAME
    }

@app.delete("/api/data/cleanup")
async def cleanup_old_data(
    days: int = Query(default=30, ge=1, le=365, description="删除N天前的数据"),
    db: Session = Depends(get_db)
):
    """清理旧数据"""
    deleted_count = SensorDataCRUD.delete_old_data(db, days=days)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"已删除 {days} 天前的 {deleted_count} 条记录"
    }

@app.get("/")
async def root():
    """
    根路由，返回index.html。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    捕获所有路由，并返回index.html，让Vue Router处理。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
