from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

# 导入数据库相关模块
from database import init_db, get_db, SessionLocal, SensorDataCRUD
from models import SensorData
from config import settings
from ml_api import router as ml_router
from ml_service import ml_service

app = FastAPI()
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
# 当前采样率（毫秒）
current_sampling_rate_ms = 5000
# 高采样模式的采样率
HIGH_SAMPLE_RATE_MS = 1000
# 常规采样率
NORMAL_SAMPLE_RATE_MS = 5000
# 上次决策状态（避免重复发送指令）
last_decision_state: Dict[str, str] = {}

async def send_sampling_rate_to_device(writer: asyncio.StreamWriter, rate_ms: int, peer_ip: str = "unknown"):
    """向硬件发送采样率指令"""
    try:
        cmd = json.dumps({"cmd": "set_rate", "rate_ms": rate_ms}) + "\n"
        writer.write(cmd.encode())
        await writer.drain()
        print(f"✓ 向设备 {peer_ip} 发送采样率指令: {rate_ms}ms")
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

async def handle_tcp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """处理单个TCP客户端，按行解析JSON，支持双向通信"""
    addr = writer.get_extra_info("peername")
    peer_ip = addr[0] if addr else "unknown"
    print(f"✓ TCP客户端连接: {peer_ip}")

    # 保存writer引用，支持双向通信
    active_tcp_writers[peer_ip] = writer
    last_decision_state[peer_ip] = "normal"

    try:
        while True:
            data = await reader.readline()
            if not data:
                break

            try:
                json_str = data.decode("utf-8").strip()
                if not json_str:
                    continue
                sensor_data = json.loads(json_str)
                sensor_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

            except json.JSONDecodeError as e:
                print(f"✗ JSON解析失败: {e}, 原始数据: {data}")
            except Exception as e:
                print(f"✗ 处理数据失败: {e}")
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
