"""
ECSS PUS（Packet Utilisation Standard）最小子集实现（SpaceNose PUS-C Profile）

说明：
- 采用 CCSDS Space Packet Primary Header（6B）+ ECSS PUS-C Secondary Header
  - TC: 5B（Ver/Ack + SrvType + SrvSubType + SourceId(16)）
  - TM: 7B（Ver/TimeRef + SrvType + SrvSubType + Subcounter(16) + DestId(16)）
  - Packet Error Control: CRC16(2B)（附在包尾）
- 仅实现本项目联调所需的最小功能：TM(1/3/5) + TC(129)
- 传输层无关：可跑在 TCP/LoRa/串口等任意字节流/报文之上
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

CCSDS_PRIMARY_HEADER_LEN = 6
PUS_C_TC_SECONDARY_HEADER_LEN = 5
PUS_C_TM_SECONDARY_HEADER_LEN = 7
PUS_C_CRC_LEN = 2

CCSDS_VERSION = 0
CCSDS_SEQ_FLAG_UNSEGMENTED = 0x3

PUS_VERSION = 2

# 默认任务配置（可按需改为配置项）
DEFAULT_APID = 0x001
DEFAULT_SOURCE_ID = 0x0001
DEFAULT_DEST_ID = 0x0000

# PUS 服务号（最小子集）
PUS_SERVICE_TC_VERIFICATION = 1
PUS_SERVICE_HOUSEKEEPING = 3
PUS_SERVICE_EVENT_REPORTING = 5

# 任务自定义服务（ECSS PUS 允许 128~255 自定义）
PUS_SERVICE_MISSION = 129
MISSION_SUBTYPE_SET_RATE = 1
MISSION_SUBTYPE_TM_ACK = 2

# Service 3: Housekeeping
PUS3_HK_REPORT = 25

# Service 1: TC Verification（仅用到 acceptance/completion）
PUS1_ACCEPTANCE_SUCCESS = 1
PUS1_ACCEPTANCE_FAILURE = 2
PUS1_COMPLETION_SUCCESS = 7
PUS1_COMPLETION_FAILURE = 8

# Service 5: Event reporting（用 subtype 表示严重级别）
PUS5_EVENT_INFO = 1
PUS5_EVENT_LOW = 2
PUS5_EVENT_MEDIUM = 3
PUS5_EVENT_HIGH = 4


def _u16(b: bytes) -> int:
    return int.from_bytes(b, "big", signed=False)


def _p16(value: int) -> bytes:
    return int(value & 0xFFFF).to_bytes(2, "big", signed=False)


def crc16_ccitt(data: bytes, *, init: int = 0xFFFF) -> int:
    """
    CRC-16-CCITT（poly=0x1021, init=0xFFFF, no-reflect, xorout=0x0000）。
    用作 ECSS PUS-C Packet Error Control Field。
    """
    crc = init & 0xFFFF
    for b in data:
        crc ^= (b & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


@dataclass(frozen=True)
class CcsdsPrimaryHeader:
    pkt_type: int  # 0=TM, 1=TC
    apid: int
    seq_flags: int
    seq_count: int
    pkt_length: int  # Packet Length field (data_field_len - 1)

    @property
    def total_len(self) -> int:
        # Total packet = primary(6) + data_field_len(pkt_length+1)
        return CCSDS_PRIMARY_HEADER_LEN + self.pkt_length + 1


@dataclass(frozen=True)
class PusPacket:
    primary: CcsdsPrimaryHeader
    pus_version: int
    service_type: int
    service_subtype: int
    ack: int  # TC only; TM 为 0
    time_ref: int  # TM only; TC 为 0
    source_id: Optional[int]  # TC only (16-bit)
    dest_id: Optional[int]  # TM only (16-bit)
    subcounter: Optional[int]  # TM only (16-bit)
    user_data: bytes
    crc: int
    crc_ok: bool

    @property
    def is_tm(self) -> bool:
        return self.primary.pkt_type == 0

    @property
    def is_tc(self) -> bool:
        return self.primary.pkt_type == 1


def parse_primary_header(header: bytes) -> CcsdsPrimaryHeader:
    if len(header) < CCSDS_PRIMARY_HEADER_LEN:
        raise ValueError("CCSDS header too short")

    packet_id = _u16(header[0:2])
    version = (packet_id >> 13) & 0x7
    if version != CCSDS_VERSION:
        raise ValueError(f"Unsupported CCSDS version: {version}")

    pkt_type = (packet_id >> 12) & 0x1
    sec_hdr_flag = (packet_id >> 11) & 0x1
    if sec_hdr_flag != 1:
        raise ValueError("Secondary header flag is 0 (unsupported)")

    apid = packet_id & 0x07FF
    seq_ctrl = _u16(header[2:4])
    seq_flags = (seq_ctrl >> 14) & 0x3
    seq_count = seq_ctrl & 0x3FFF
    pkt_length = _u16(header[4:6])

    return CcsdsPrimaryHeader(
        pkt_type=pkt_type,
        apid=apid,
        seq_flags=seq_flags,
        seq_count=seq_count,
        pkt_length=pkt_length,
    )


def looks_like_primary_header(buf: bytes, *, max_len: int = 2048) -> bool:
    if len(buf) < CCSDS_PRIMARY_HEADER_LEN:
        return False
    try:
        primary = parse_primary_header(buf[:CCSDS_PRIMARY_HEADER_LEN])
    except Exception:
        return False
    min_len = CCSDS_PRIMARY_HEADER_LEN + PUS_C_CRC_LEN
    if primary.pkt_type == 1:
        min_len += PUS_C_TC_SECONDARY_HEADER_LEN
    else:
        min_len += PUS_C_TM_SECONDARY_HEADER_LEN

    if primary.total_len < min_len:
        return False
    if primary.total_len > max_len:
        return False
    if primary.seq_flags != CCSDS_SEQ_FLAG_UNSEGMENTED:
        # 本项目联调阶段只接受未分段包
        return False
    return True


def parse_pus_packet(packet: bytes) -> PusPacket:
    if len(packet) < (CCSDS_PRIMARY_HEADER_LEN + PUS_C_CRC_LEN + PUS_C_TC_SECONDARY_HEADER_LEN):
        raise ValueError("PUS-C packet too short")

    primary = parse_primary_header(packet[:CCSDS_PRIMARY_HEADER_LEN])
    if len(packet) != primary.total_len:
        raise ValueError("PUS packet length mismatch")

    data_field = packet[CCSDS_PRIMARY_HEADER_LEN:]
    if len(data_field) < PUS_C_CRC_LEN:
        raise ValueError("PUS-C data field too short")

    crc_read = _u16(data_field[-2:])
    crc_calc = crc16_ccitt(packet[:-2])
    crc_ok = crc_read == crc_calc
    if not crc_ok:
        raise ValueError(f"CRC mismatch: read=0x{crc_read:04X} calc=0x{crc_calc:04X}")

    if primary.pkt_type == 1:
        if len(data_field) < (PUS_C_TC_SECONDARY_HEADER_LEN + PUS_C_CRC_LEN):
            raise ValueError("PUS-C TC secondary header too short")
        sec = data_field[:PUS_C_TC_SECONDARY_HEADER_LEN]
        ver_and_ack = sec[0]
        pus_version = (ver_and_ack >> 4) & 0xF
        if pus_version != PUS_VERSION:
            raise ValueError(f"Unsupported PUS version: {pus_version}")

        ack = ver_and_ack & 0x0F
        time_ref = 0
        service_type = sec[1]
        service_subtype = sec[2]
        source_id = _u16(sec[3:5])
        dest_id = None
        subcounter = None
        user_data = data_field[PUS_C_TC_SECONDARY_HEADER_LEN:-2]
    else:
        if len(data_field) < (PUS_C_TM_SECONDARY_HEADER_LEN + PUS_C_CRC_LEN):
            raise ValueError("PUS-C TM secondary header too short")
        sec = data_field[:PUS_C_TM_SECONDARY_HEADER_LEN]
        ver_and_time = sec[0]
        pus_version = (ver_and_time >> 4) & 0xF
        if pus_version != PUS_VERSION:
            raise ValueError(f"Unsupported PUS version: {pus_version}")

        time_ref = ver_and_time & 0x0F
        ack = 0
        service_type = sec[1]
        service_subtype = sec[2]
        subcounter = _u16(sec[3:5])
        dest_id = _u16(sec[5:7])
        source_id = None
        user_data = data_field[PUS_C_TM_SECONDARY_HEADER_LEN:-2]

    return PusPacket(
        primary=primary,
        pus_version=pus_version,
        service_type=service_type,
        service_subtype=service_subtype,
        ack=ack,
        time_ref=time_ref,
        source_id=source_id,
        dest_id=dest_id,
        subcounter=subcounter,
        user_data=user_data,
        crc=crc_read,
        crc_ok=crc_ok,
    )


def build_primary_header(*, pkt_type: int, apid: int, seq_count: int, data_field_len: int) -> bytes:
    if data_field_len <= 0:
        raise ValueError("data_field_len must be > 0")
    if data_field_len > 0xFFFF + 1:
        raise ValueError("data_field_len too large")

    packet_id = (CCSDS_VERSION & 0x7) << 13
    packet_id |= (int(pkt_type) & 0x1) << 12
    packet_id |= 1 << 11
    packet_id |= int(apid) & 0x07FF

    seq_ctrl = (CCSDS_SEQ_FLAG_UNSEGMENTED & 0x3) << 14
    seq_ctrl |= int(seq_count) & 0x3FFF

    pkt_length = int(data_field_len - 1) & 0xFFFF

    return _p16(packet_id) + _p16(seq_ctrl) + _p16(pkt_length)


def build_tm(
    *,
    apid: int,
    seq_count: int,
    service_type: int,
    service_subtype: int,
    subcounter: int = 0,
    dest_id: int = DEFAULT_DEST_ID,
    time_ref: int = 0,
    user_data: bytes = b"",
) -> bytes:
    sec0 = ((PUS_VERSION & 0xF) << 4) | (int(time_ref) & 0x0F)
    secondary = (
        bytes([sec0, service_type & 0xFF, service_subtype & 0xFF])
        + _p16(int(subcounter))
        + _p16(int(dest_id))
    )

    body = secondary + (user_data or b"")
    primary = build_primary_header(pkt_type=0, apid=apid, seq_count=seq_count, data_field_len=len(body) + PUS_C_CRC_LEN)
    pkt_wo_crc = primary + body
    crc = crc16_ccitt(pkt_wo_crc)
    return pkt_wo_crc + _p16(crc)


def build_tc(
    *,
    apid: int,
    seq_count: int,
    service_type: int,
    service_subtype: int,
    source_id: int = DEFAULT_SOURCE_ID,
    ack: int = 0x9,  # acceptance + completion
    user_data: bytes = b"",
) -> bytes:
    sec0 = ((PUS_VERSION & 0xF) << 4) | (ack & 0x0F)
    secondary = bytes([sec0, service_type & 0xFF, service_subtype & 0xFF]) + _p16(int(source_id))

    body = secondary + (user_data or b"")
    primary = build_primary_header(pkt_type=1, apid=apid, seq_count=seq_count, data_field_len=len(body) + PUS_C_CRC_LEN)
    pkt_wo_crc = primary + body
    crc = crc16_ccitt(pkt_wo_crc)
    return pkt_wo_crc + _p16(crc)


def make_tc_set_rate(*, rate_ms: int, apid: int, seq_count: int) -> bytes:
    payload = ("{\"cmd\":\"set_rate\",\"rate_ms\":%d}" % int(rate_ms)).encode("utf-8")
    return build_tc(
        apid=apid,
        seq_count=seq_count,
        service_type=PUS_SERVICE_MISSION,
        service_subtype=MISSION_SUBTYPE_SET_RATE,
        user_data=payload,
    )


def make_tc_tm_ack(*, tm_packet_id: int, tm_seq_ctrl: int, apid: int, seq_count: int) -> bytes:
    user_data = _p16(tm_packet_id) + _p16(tm_seq_ctrl)
    return build_tc(
        apid=apid,
        seq_count=seq_count,
        service_type=PUS_SERVICE_MISSION,
        service_subtype=MISSION_SUBTYPE_TM_ACK,
        user_data=user_data,
        ack=0x0,  # 不请求 verification（事件ACK本身不需要再回包）
    )


def unpack_tc_verification_user_data(user_data: bytes) -> Optional[tuple[int, int]]:
    """
    Service 1 verification user data（最小）：[packet_id(2)][seq_ctrl(2)]。
    返回 (packet_id, seq_ctrl)；长度不足则返回 None。
    """
    if len(user_data) < 4:
        return None
    return _u16(user_data[0:2]), _u16(user_data[2:4])
