# ECSS PUS 联调指南（TCP / LoRa 网关）

本指南用于验证以下链路闭环：
- STM32 上行 **PUS TM**（Service 3/25：Housekeeping；Service 5：Event）
- 后端解析、入库、WebSocket 广播
- 后端下发 **PUS TC**（Service 129/1：set_rate），设备回 **Service 1** Verification
- 事件可靠下传：地面回 **Service 129/2** TM‑ACK，设备停止重传

---

## 1) TCP 直连联调（ESP8266 原型链路）

1. 启动后端（地面）
   - 在 `backend/` 运行：`python main.py`
2. 烧录固件（星上/载荷）
   - STM32 启动后连接 Wi‑Fi 并建立 TCP 到后端（端口见 `backend/config.py` 与 `src/main.c`）
   - 连通后持续上行：
     - TM(3/25) Housekeeping：传感器采样 JSON
     - TM(5/x) Event：状态变化/阈值触发（带重传，等待 TM‑ACK）
3. 验证事件下传
   - 让 `alcohol_ppm` 超过 `ALCOHOL_ALERT_PPM`（见 `src/main.c`）触发事件
   - 后端日志应出现 `✓(PUS) 收到事件`
4. 验证下行 set_rate（地面→设备）
   - 调用 `POST /api/pus/set_rate`
   - 设备应更新采样间隔；后端日志应出现 `✓(PUS) TC验收回报` 与 `✓(PUS) TC完成回报`

示例（将 `peer_id` 换成设备 TCP 连接的 IP）：
```bash
curl -X POST http://127.0.0.1:8000/api/pus/set_rate ^
  -H "Content-Type: application/json" ^
  -d "{\"peer_id\":\"192.168.137.10\",\"rate_ms\":1000}"
```

---

## 2) LoRa/串口网关模式（推荐走 HTTP ingest）

网关职责建议拆分为一个独立程序：
- 上行：从 LoRa/串口收到 **二进制 PUS 包** → base64 → `POST /api/pus/ingest`
- 下行：若响应包含 `ack_packet_b64` → base64 解码 → 再通过 LoRa/串口回传给设备

### 2.1 上行接口

- `POST /api/pus/ingest`
- body：
  - `peer_id`: 例如 `lora:dev1`
  - `packet_b64`: 二进制 PUS 包的 base64
- 响应：
  - `ack_packet_b64`: 可能为 `null`；若为事件 TM‑ACK，网关应回传给设备

---

## 3) 协议文档

- `docs/PUS_PROFILE.md`

