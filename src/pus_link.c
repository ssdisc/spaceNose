#include "pus_link.h"

#include "stm32f4xx_hal.h"

#include <string.h>

/* ===================== Profile 参数（按需调整） ===================== */

#define PUS_VERSION 2

#define CCSDS_VERSION 0
#define CCSDS_PRIMARY_HEADER_LEN 6
#define CCSDS_SEQ_FLAG_UNSEGMENTED 0x3

#define PUS_C_TC_SEC_LEN 5
#define PUS_C_TM_SEC_LEN 7
#define PUS_C_CRC_LEN 2

#define PUS_MAX_PACKET_LEN 256
#define PUS_QUEUE_SIZE 16

#define PUS_RETRY_INTERVAL_MS 1500
#define PUS_MAX_RETRIES 5

/* PUS services */
#define PUS_SERVICE_TC_VERIFICATION 1
#define PUS_SERVICE_HOUSEKEEPING 3
#define PUS_SERVICE_EVENT_REPORTING 5

/* Service 3 */
#define PUS3_HK_REPORT 25

/* Service 1 subtypes */
#define PUS1_ACCEPTANCE_SUCCESS 1
#define PUS1_ACCEPTANCE_FAILURE 2
#define PUS1_COMPLETION_SUCCESS 7
#define PUS1_COMPLETION_FAILURE 8

/* Mission-specific service 129 */
#define PUS_SERVICE_MISSION 129
#define MISSION_SUBTYPE_SET_RATE 1
#define MISSION_SUBTYPE_TM_ACK 2

typedef struct {
    uint8_t used;
    uint8_t prio;
    uint8_t ack_required;
    uint32_t last_send_ms;
    uint8_t retries;
    uint16_t len;
    uint16_t packet_id;
    uint16_t seq_ctrl;
    uint8_t buf[PUS_MAX_PACKET_LEN];
} pus_msg_t;

static pus_link_send_fn_t g_send_fn = NULL;
static pus_link_cmd_handler_t g_cmd_handler = NULL;
static uint8_t g_connected = 0;

static uint16_t g_tm_seq = 0;
static uint16_t g_tm_subcounter = 0;

static uint16_t g_apid = 0x001;
static uint16_t g_source_id = 0x0001;
static uint16_t g_dest_id = 0x0000;

static pus_msg_t g_queue[PUS_QUEUE_SIZE];

static inline uint16_t rd_u16(const uint8_t* p) {
    return (uint16_t)((((uint16_t)p[0]) << 8) | ((uint16_t)p[1]));
}

static inline void wr_u16(uint8_t* p, uint16_t v) {
    p[0] = (uint8_t)(v >> 8);
    p[1] = (uint8_t)(v & 0xFF);
}

static uint16_t crc16_ccitt(const uint8_t* data, uint16_t len) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)((uint16_t)data[i] << 8);
        for (uint8_t b = 0; b < 8; b++) {
            if (crc & 0x8000) {
                crc = (uint16_t)((crc << 1) ^ 0x1021);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }
    return crc;
}

static void queue_clear_slot(int idx) {
    if (idx < 0 || idx >= PUS_QUEUE_SIZE) {
        return;
    }
    g_queue[idx].used = 0;
    g_queue[idx].prio = 0;
    g_queue[idx].ack_required = 0;
    g_queue[idx].last_send_ms = 0;
    g_queue[idx].retries = 0;
    g_queue[idx].len = 0;
    g_queue[idx].packet_id = 0;
    g_queue[idx].seq_ctrl = 0;
    memset(g_queue[idx].buf, 0, sizeof(g_queue[idx].buf));
}

static int queue_find_free(void) {
    for (int i = 0; i < PUS_QUEUE_SIZE; i++) {
        if (!g_queue[i].used) {
            return i;
        }
    }
    return -1;
}

static int queue_find_evict(uint8_t new_prio) {
    /* 只淘汰 ack_required=0 的低优先级消息 */
    int best_idx = -1;
    uint8_t best_prio = 255;
    for (int i = 0; i < PUS_QUEUE_SIZE; i++) {
        if (!g_queue[i].used) {
            continue;
        }
        if (g_queue[i].ack_required) {
            continue;
        }
        if (g_queue[i].prio < best_prio) {
            best_prio = g_queue[i].prio;
            best_idx = i;
        }
    }
    /* 同优先级也允许覆盖，避免断链时缓存过旧的遥测 */
    if (best_idx >= 0 && new_prio >= best_prio) {
        return best_idx;
    }
    return -1;
}

static uint8_t queue_enqueue(uint8_t prio, uint8_t ack_required, const uint8_t* packet, uint16_t len, uint16_t packet_id, uint16_t seq_ctrl) {
    if (packet == NULL || len == 0 || len > PUS_MAX_PACKET_LEN) {
        return 0;
    }

    int idx = queue_find_free();
    if (idx < 0) {
        idx = queue_find_evict(prio);
        if (idx < 0) {
            return 0;
        }
        queue_clear_slot(idx);
    }

    g_queue[idx].used = 1;
    g_queue[idx].prio = prio;
    g_queue[idx].ack_required = ack_required ? 1 : 0;
    g_queue[idx].last_send_ms = 0;
    g_queue[idx].retries = 0;
    g_queue[idx].len = len;
    g_queue[idx].packet_id = packet_id;
    g_queue[idx].seq_ctrl = seq_ctrl;
    memcpy(g_queue[idx].buf, packet, len);
    return 1;
}

static void queue_ack(uint16_t packet_id, uint16_t seq_ctrl) {
    for (int i = 0; i < PUS_QUEUE_SIZE; i++) {
        if (g_queue[i].used && g_queue[i].packet_id == packet_id && g_queue[i].seq_ctrl == seq_ctrl) {
            queue_clear_slot(i);
            return;
        }
    }
}

static uint16_t alloc_tm_seq(void) {
    uint16_t seq = (uint16_t)(g_tm_seq & 0x3FFF);
    g_tm_seq = (uint16_t)((seq + 1) & 0x3FFF);
    return seq;
}

static uint16_t alloc_tm_subcounter(void) {
    uint16_t sc = g_tm_subcounter;
    g_tm_subcounter = (uint16_t)(g_tm_subcounter + 1);
    return sc;
}

static uint16_t build_tm_packet(
    uint8_t* out,
    uint16_t out_max,
    uint8_t service_type,
    uint8_t service_subtype,
    const uint8_t* user_data,
    uint16_t user_len,
    uint16_t* out_packet_id,
    uint16_t* out_seq_ctrl
) {
    if (out == NULL || out_max < 16) {
        return 0;
    }

    uint16_t seq_count = alloc_tm_seq();
    uint16_t subcounter = alloc_tm_subcounter();

    uint16_t packet_id = (uint16_t)(((CCSDS_VERSION & 0x7) << 13) | (0 << 12) | (1 << 11) | (g_apid & 0x07FF));
    uint16_t seq_ctrl = (uint16_t)(((CCSDS_SEQ_FLAG_UNSEGMENTED & 0x3) << 14) | (seq_count & 0x3FFF));

    uint16_t data_field_len = (uint16_t)(PUS_C_TM_SEC_LEN + user_len + PUS_C_CRC_LEN);
    uint16_t total_len = (uint16_t)(CCSDS_PRIMARY_HEADER_LEN + data_field_len);
    if (total_len > out_max || total_len > PUS_MAX_PACKET_LEN) {
        return 0;
    }

    /* Primary header */
    wr_u16(&out[0], packet_id);
    wr_u16(&out[2], seq_ctrl);
    wr_u16(&out[4], (uint16_t)(data_field_len - 1));

    /* Secondary header (TM, PUS-C, no time field) */
    out[6] = (uint8_t)(((PUS_VERSION & 0xF) << 4) | 0x0);
    out[7] = service_type;
    out[8] = service_subtype;
    wr_u16(&out[9], subcounter);
    wr_u16(&out[11], g_dest_id); /* DestId */

    /* User data */
    if (user_len > 0 && user_data != NULL) {
        memcpy(&out[13], user_data, user_len);
    }

    /* CRC */
    uint16_t crc = crc16_ccitt(out, (uint16_t)(total_len - 2));
    wr_u16(&out[total_len - 2], crc);

    if (out_packet_id != NULL) {
        *out_packet_id = packet_id;
    }
    if (out_seq_ctrl != NULL) {
        *out_seq_ctrl = seq_ctrl;
    }
    return total_len;
}

static uint8_t send_packet_now(const uint8_t* packet, uint16_t len) {
    if (!g_send_fn || !packet || len == 0) {
        return 0;
    }
    return g_send_fn(packet, len);
}

static void send_tc_verification(uint8_t subtype, uint16_t tc_packet_id, uint16_t tc_seq_ctrl) {
    if (!g_connected) {
        return;
    }

    uint8_t user_data[4];
    wr_u16(&user_data[0], tc_packet_id);
    wr_u16(&user_data[2], tc_seq_ctrl);

    uint8_t pkt[PUS_MAX_PACKET_LEN];
    uint16_t tm_pid = 0;
    uint16_t tm_sc = 0;
    uint16_t n = build_tm_packet(
        pkt,
        sizeof(pkt),
        PUS_SERVICE_TC_VERIFICATION,
        subtype,
        user_data,
        sizeof(user_data),
        &tm_pid,
        &tm_sc
    );
    if (n == 0) {
        return;
    }
    send_packet_now(pkt, n);
}

static uint8_t event_subtype_to_prio(uint8_t subtype) {
    if (subtype >= PUS5_EVENT_HIGH) {
        return 3;
    }
    if (subtype == PUS5_EVENT_MEDIUM) {
        return 2;
    }
    if (subtype == PUS5_EVENT_LOW) {
        return 1;
    }
    return 0;
}

/* 接收缓冲：用于从字节流中拼出完整 PUS 包 */
#define PUS_RX_BUF_SIZE 512
static uint8_t g_rx_buf[PUS_RX_BUF_SIZE];
static uint16_t g_rx_len = 0;

static uint8_t looks_like_ccsds_header(const uint8_t* buf, uint16_t buf_len, uint16_t* out_total_len) {
    if (buf == NULL || buf_len < CCSDS_PRIMARY_HEADER_LEN) {
        return 0;
    }
    uint16_t packet_id = rd_u16(&buf[0]);
    uint8_t version = (uint8_t)((packet_id >> 13) & 0x7);
    uint8_t sec_flag = (uint8_t)((packet_id >> 11) & 0x1);
    if (version != CCSDS_VERSION || sec_flag != 1) {
        return 0;
    }
    uint16_t seq_ctrl = rd_u16(&buf[2]);
    uint8_t seq_flags = (uint8_t)((seq_ctrl >> 14) & 0x3);
    if (seq_flags != CCSDS_SEQ_FLAG_UNSEGMENTED) {
        return 0;
    }
    uint16_t pkt_length = rd_u16(&buf[4]);
    uint16_t total = (uint16_t)(pkt_length + 7);
    if (total < 13 || total > PUS_MAX_PACKET_LEN || total > PUS_RX_BUF_SIZE) {
        return 0;
    }
    if (out_total_len != NULL) {
        *out_total_len = total;
    }
    return 1;
}

static void handle_packet(const uint8_t* packet, uint16_t len) {
    if (packet == NULL || len < (CCSDS_PRIMARY_HEADER_LEN + PUS_C_TC_SEC_LEN + PUS_C_CRC_LEN)) {
        return;
    }

    /* 校验 CRC（包尾 2B） */
    uint16_t crc_read = rd_u16(&packet[len - 2]);
    uint16_t crc_calc = crc16_ccitt(packet, (uint16_t)(len - 2));
    if (crc_read != crc_calc) {
        return;
    }

    uint16_t packet_id = rd_u16(&packet[0]);
    uint8_t version = (uint8_t)((packet_id >> 13) & 0x7);
    uint8_t pkt_type = (uint8_t)((packet_id >> 12) & 0x1);
    uint8_t sec_flag = (uint8_t)((packet_id >> 11) & 0x1);
    if (version != CCSDS_VERSION || sec_flag != 1) {
        return;
    }
    if (pkt_type != 1) {
        /* 仅处理地面下发 TC */
        return;
    }

    uint16_t seq_ctrl = rd_u16(&packet[2]);
    uint16_t pkt_length = rd_u16(&packet[4]);
    uint16_t total_len = (uint16_t)(pkt_length + 7);
    if (total_len != len) {
        return;
    }

    /* PUS-C TC secondary header */
    uint8_t sec0 = packet[6];
    uint8_t pus_ver = (uint8_t)((sec0 >> 4) & 0xF);
    uint8_t ack = (uint8_t)(sec0 & 0x0F);
    if (pus_ver != PUS_VERSION) {
        return;
    }
    uint8_t service_type = packet[7];
    uint8_t service_subtype = packet[8];

    /* SourceId(16) */
    /* uint16_t source_id = rd_u16(&packet[9]); */

    const uint8_t* user_data = &packet[11];
    uint16_t user_len = (uint16_t)(len - CCSDS_PRIMARY_HEADER_LEN - PUS_C_TC_SEC_LEN - PUS_C_CRC_LEN);

    /* 任务自定义：TM-ACK（129/2） */
    if (service_type == PUS_SERVICE_MISSION && service_subtype == MISSION_SUBTYPE_TM_ACK) {
        if (user_len >= 4) {
            uint16_t tm_pid = rd_u16(&user_data[0]);
            uint16_t tm_sc = rd_u16(&user_data[2]);
            queue_ack(tm_pid, tm_sc);
        }
        return;
    }

    /* 任务自定义：set_rate（129/1，user_data 为 JSON） */
    uint8_t need_accept = (ack & 0x01) ? 1 : 0;
    uint8_t need_completion = (ack & 0x08) ? 1 : 0;

    uint8_t can_handle = (service_type == PUS_SERVICE_MISSION && service_subtype == MISSION_SUBTYPE_SET_RATE) ? 1 : 0;
    if (need_accept) {
        send_tc_verification(can_handle ? PUS1_ACCEPTANCE_SUCCESS : PUS1_ACCEPTANCE_FAILURE, packet_id, seq_ctrl);
    }
    if (!can_handle) {
        return;
    }

    if (g_cmd_handler && user_len > 0) {
        char json_buf[256];
        uint16_t n = (user_len < (uint16_t)(sizeof(json_buf) - 1)) ? user_len : (uint16_t)(sizeof(json_buf) - 1);
        memcpy(json_buf, user_data, n);
        json_buf[n] = '\0';
        g_cmd_handler(json_buf);
    }

    if (need_completion) {
        send_tc_verification(PUS1_COMPLETION_SUCCESS, packet_id, seq_ctrl);
    }
}

void PusLink_Init(pus_link_send_fn_t send_fn, uint16_t apid, uint16_t source_id, uint16_t dest_id) {
    g_send_fn = send_fn;
    g_cmd_handler = NULL;
    g_connected = 0;
    g_tm_seq = 0;
    g_tm_subcounter = 0;
    g_apid = (uint16_t)(apid & 0x07FF);
    g_source_id = source_id;
    g_dest_id = dest_id;
    g_rx_len = 0;
    memset(g_rx_buf, 0, sizeof(g_rx_buf));
    for (int i = 0; i < PUS_QUEUE_SIZE; i++) {
        queue_clear_slot(i);
    }
}

void PusLink_SetConnected(uint8_t connected) {
    g_connected = connected ? 1 : 0;
}

void PusLink_SetCommandHandler(pus_link_cmd_handler_t handler) {
    g_cmd_handler = handler;
}

void PusLink_FeedBytes(const uint8_t* data, uint16_t len) {
    if (data == NULL || len == 0) {
        return;
    }

    while (len > 0) {
        uint16_t space = (uint16_t)(sizeof(g_rx_buf) - g_rx_len);
        uint16_t n = (len < space) ? len : space;
        if (n == 0) {
            /* 溢出：清空并重新同步 */
            g_rx_len = 0;
            break;
        }
        memcpy(&g_rx_buf[g_rx_len], data, n);
        g_rx_len = (uint16_t)(g_rx_len + n);
        data += n;
        len = (uint16_t)(len - n);

        while (g_rx_len >= CCSDS_PRIMARY_HEADER_LEN) {
            uint16_t total = 0;
            if (!looks_like_ccsds_header(g_rx_buf, g_rx_len, &total)) {
                /* 不像包头：丢 1 字节后继续找同步 */
                memmove(g_rx_buf, &g_rx_buf[1], (size_t)(g_rx_len - 1));
                g_rx_len = (uint16_t)(g_rx_len - 1);
                continue;
            }
            if (g_rx_len < total) {
                break;
            }
            handle_packet(g_rx_buf, total);
            memmove(g_rx_buf, &g_rx_buf[total], (size_t)(g_rx_len - total));
            g_rx_len = (uint16_t)(g_rx_len - total);
        }
    }
}

uint8_t PusLink_QueueHousekeeping(const char* payload_json) {
    if (payload_json == NULL) {
        return 0;
    }
    uint16_t user_len = (uint16_t)strlen(payload_json);
    uint8_t pkt[PUS_MAX_PACKET_LEN];
    uint16_t pid = 0;
    uint16_t sc = 0;
    uint16_t n = build_tm_packet(
        pkt,
        sizeof(pkt),
        PUS_SERVICE_HOUSEKEEPING,
        PUS3_HK_REPORT,
        (const uint8_t*)payload_json,
        user_len,
        &pid,
        &sc
    );
    if (n == 0) {
        return 0;
    }
    return queue_enqueue(0, 0, pkt, n, pid, sc);
}

uint8_t PusLink_QueueEvent(uint8_t event_subtype, const char* payload_json, uint8_t ack_required) {
    if (payload_json == NULL) {
        return 0;
    }
    uint16_t user_len = (uint16_t)strlen(payload_json);
    uint8_t pkt[PUS_MAX_PACKET_LEN];
    uint16_t pid = 0;
    uint16_t sc = 0;
    uint16_t n = build_tm_packet(
        pkt,
        sizeof(pkt),
        PUS_SERVICE_EVENT_REPORTING,
        event_subtype,
        (const uint8_t*)payload_json,
        user_len,
        &pid,
        &sc
    );
    if (n == 0) {
        return 0;
    }
    uint8_t prio = event_subtype_to_prio(event_subtype);
    return queue_enqueue(prio, ack_required, pkt, n, pid, sc);
}

uint8_t PusLink_Poll(void) {
    if (!g_connected || g_send_fn == NULL) {
        return 1;
    }

    uint32_t now = HAL_GetTick();

    int best_idx = -1;
    uint8_t best_prio = 0;
    uint8_t best_unsent = 0;

    for (int i = 0; i < PUS_QUEUE_SIZE; i++) {
        if (!g_queue[i].used) {
            continue;
        }

        uint8_t can_send = 0;
        if (g_queue[i].last_send_ms == 0) {
            can_send = 1;
        } else if (g_queue[i].ack_required) {
            if ((now - g_queue[i].last_send_ms) >= PUS_RETRY_INTERVAL_MS && g_queue[i].retries < PUS_MAX_RETRIES) {
                can_send = 1;
            }
        }

        if (!can_send) {
            continue;
        }

        uint8_t unsent = (g_queue[i].last_send_ms == 0) ? 1 : 0;

        if (best_idx < 0) {
            best_idx = i;
            best_prio = g_queue[i].prio;
            best_unsent = unsent;
            continue;
        }

        if (g_queue[i].prio > best_prio) {
            best_idx = i;
            best_prio = g_queue[i].prio;
            best_unsent = unsent;
            continue;
        }

        if (g_queue[i].prio == best_prio && unsent > best_unsent) {
            best_idx = i;
            best_unsent = unsent;
            continue;
        }
    }

    if (best_idx < 0) {
        return 1;
    }

    uint8_t ok = send_packet_now(g_queue[best_idx].buf, g_queue[best_idx].len);
    if (!ok) {
        return 0;
    }

    g_queue[best_idx].last_send_ms = now;
    if (g_queue[best_idx].ack_required) {
        if (g_queue[best_idx].retries < 255) {
            g_queue[best_idx].retries++;
        }
    } else {
        queue_clear_slot(best_idx);
    }
    return 1;
}
