# ECSS PUS（SpaceNose Profile）

本项目“星上载荷（STM32） ↔ 地面后端（FastAPI）”链路已改用 **ECSS Packet Utilisation Standard (PUS)** 的最小子集（profile），用于遥测（TM）与遥控（TC）。

> 说明：PUS 不规定底层传输，本项目当前跑在 TCP（原型链路），也可承载于 LoRa/串口透传（配合网关）。

---

## 1) 分层与分帧

- **包结构（PUS-C）**：CCSDS Space Packet Primary Header（6B） + PUS-C Secondary Header（TC:5B / TM:7B） + User Data（任务自定义） + CRC16（2B）
- **CCSDS 约束**：
  - Version = `0`
  - Secondary header flag = `1`
  - Sequence flags = `3`（Unsegmented）
- **PUS 约束**：
  - PUS Version = `2`
- **APID（需两端一致）**：`0x001`（backend `backend/pus.py` 与固件 `src/pus_link.c` 默认一致）
- **CRC16（Packet Error Control Field）**：CRC‑16‑CCITT（poly=`0x1021`, init=`0xFFFF`, no‑reflect, xorout=`0x0000`），附在包尾 2 字节（big‑endian）。

---

## 2) PUS Secondary Header（本项目约定）

- **TM（PUS‑C，无 time 字段）**：
  - `[ver(4)=2 | time_ref(4)=0] [service] [subservice] [subcounter(16)] [dest_id(16)]`
- **TC（PUS‑C）**：
  - `[ver(4)=2 | ack(4)] [service] [subservice] [source_id(16)]`

ACK(4) 位定义（本项目遵循常见 PUS 习惯）：
- bit0：Acceptance
- bit1：Start
- bit2：Progress
- bit3：Completion

> User Data 为任务自定义。联调阶段统一使用 **UTF‑8 JSON（不含换行）** 承载 payload，便于调试与网关转发。

---

## 3) 服务/子服务映射（最小子集）

### 3.1 TM：Housekeeping（周期遥测）

- **Service 3 / Subtype 25**
- **User Data**：JSON（示例字段与后端入库/可视化一致）
  - 示例：`{"counter":9,"adc":1234,"voltage":1.234,"mq3_adc":1234,"mq3_voltage":1.234,"alcohol_ppm":12.3,"sensor_status":0}`

### 3.2 TM：Event reporting（事件下传）

- **Service 5 / Subtype 1~4**：严重级别
  - `1` info / `2` low / `3` medium / `4` high
- **User Data**：JSON
  - 示例：`{"kind":"gas_alert","metric":"alcohol_ppm","value":120.5,"action":"high_sample","rate_ms":1000}`

地面在收到事件 TM 后会回一条 **TM‑ACK Telecommand**（见 3.4），用于星上可靠下传/去重/停止重传。

### 3.3 TC：Set sampling rate（任务自定义服务）

- **Service 129 / Subtype 1**
- **ACK flags**：`0x9`（request acceptance + completion）
- **User Data**：JSON
  - 示例：`{"cmd":"set_rate","rate_ms":1000}`

设备在收到后回 **TC Verification**（TM Service 1）：
- **Service 1 / Subtype 1**：Acceptance success
- **Service 1 / Subtype 7**：Completion success
- Verification **User Data（4B）**：`[tc_packet_id(2)][tc_seq_ctrl(2)]`，big‑endian（随后仍带 CRC16）

### 3.4 TC：TM‑ACK（任务自定义服务）

- **Service 129 / Subtype 2**
- **ACK flags**：`0x0`（不请求 verification；减少回包）
- **User Data（4B）**：`[tm_packet_id(2)][tm_seq_ctrl(2)]`，big‑endian
- **用途**：地面对事件 TM 的“已收到”确认；设备据此从重传队列移除对应事件。

---

## 4) 后端接口（网关/联调）

- TCP 直连：`backend/main.py` 的 TCP server 直接收发二进制 PUS 包
- LoRa/串口网关：
  - `POST /api/pus/ingest`：上行 `packet_b64`（base64）；响应可能包含 `ack_packet_b64`
  - `POST /api/pus/set_rate`：生成/可选直连下发 set_rate TC；返回 `packet_b64`
- 调试：
  - `GET /api/pus/events`：查看最近事件下传记录（内存缓存）
