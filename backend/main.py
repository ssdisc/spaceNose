from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import asyncio
import socket
import json
from datetime import datetime
from typing import List

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

# UDP服务器配置
UDP_HOST = "0.0.0.0"  # 监听所有网络接口
UDP_PORT = 8888

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
    """启动UDP服务器"""
    asyncio.create_task(udp_server())
    print("========================================")
    print("  星际嗅探者 - 后端服务器启动")
    print(f"  HTTP服务: http://127.0.0.1:8000")
    print(f"  UDP服务: {UDP_HOST}:{UDP_PORT}")
    print(f"  WebSocket: ws://127.0.0.1:8000/ws")
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
    """获取最新的传感器数据"""
    return latest_data

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
