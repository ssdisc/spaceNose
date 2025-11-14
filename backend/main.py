from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import asyncio
import socket
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

# 导入数据库相关模块
from database import init_db, get_db, SessionLocal, SensorDataCRUD
from models import SensorData
from config import settings

app = FastAPI()

# 静态文件目录，指向Vue项目的dist目录
static_folder = os.path.join(os.path.dirname(__file__), "..", "web", "dist")

# 挂载静态文件
static_dirs = ["assets", "css", "js", "img"]
for static_dir in static_dirs:
    path = os.path.join(static_folder, static_dir)
    if os.path.exists(path) and os.path.isdir(path):
        app.mount(f"/{static_dir}", StaticFiles(directory=path), name=static_dir)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✓ WebSocket客户端已连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
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

# UDP服务器配置（从配置文件读取）
UDP_HOST = settings.UDP_HOST
UDP_PORT = settings.UDP_PORT

# 存储最新的传感器数据
latest_data = {
    "counter": 0,
    "adc": 0,
    "voltage": 0.0,
    "timestamp": ""
}

async def udp_server():
    """UDP服务器，接收来自ESP8266的数据"""
    loop = asyncio.get_event_loop()
    
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    sock.setblocking(False)
    
    print(f"✓ UDP服务器启动在 {UDP_HOST}:{UDP_PORT}")
    
    while True:
        try:
            # 非阻塞接收数据
            data, addr = await loop.sock_recvfrom(sock, 1024)
            
            # 解析JSON数据
            try:
                json_str = data.decode('utf-8').strip()
                sensor_data = json.loads(json_str)
                sensor_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 更新最新数据
                global latest_data
                latest_data = sensor_data
                
                print(f"✓ 收到数据: {sensor_data}")
                
                # 保存到数据库
                try:
                    db = SessionLocal()
                    SensorDataCRUD.create(
                        db=db,
                        counter=sensor_data.get('counter', 0),
                        adc=sensor_data.get('adc', 0),
                        voltage=sensor_data.get('voltage', 0.0),
                        source_ip=addr[0]  # 记录来源IP
                    )
                    db.close()
                except Exception as db_error:
                    print(f"⚠ 数据库保存失败: {db_error}")
                
                # 广播给所有WebSocket客户端
                await manager.broadcast(json.dumps(sensor_data))
                
            except json.JSONDecodeError as e:
                print(f"✗ JSON解析失败: {e}, 原始数据: {data}")
            except Exception as e:
                print(f"✗ 处理数据失败: {e}")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            # 如果没有数据，等待一小段时间
            await asyncio.sleep(0.01)

@app.on_event("startup")
async def startup_event():
    """启动UDP服务器和初始化数据库"""
    # 初始化数据库
    print("========================================")
    print("  星际嗅探者 - 后端服务器启动")
    print("========================================")
    
    if init_db():
        print(f"✓ 数据库连接成功: {settings.DB_NAME}")
    else:
        print("⚠ 数据库连接失败，请检查配置")
    
    # 启动UDP服务器
    asyncio.create_task(udp_server())
    
    print(f"✓ HTTP服务: http://127.0.0.1:{settings.SERVER_PORT}")
    print(f"✓ UDP服务: {UDP_HOST}:{UDP_PORT}")
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

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    捕获所有路由，并返回index.html，让Vue Router处理。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}

@app.get("/")
async def root():
    """
    根路由，返回index.html。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
