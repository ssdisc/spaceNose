#ifndef __PUS_LINK_H
#define __PUS_LINK_H

#include <stdint.h>

/**
 * ECSS PUS-C（70-41C）星地应用层协议（SpaceNose Profile）
 *
 * - 上行：TM（Housekeeping 3/25；Event 5/1~4；TC Verification 1/*）
 * - 下行：TC（任务自定义 129/1 set_rate；129/2 TM-ACK）
 *
 * 该模块负责：
 * - 断链缓存：消息队列（ring buffer）
 * - 优先级：高优先级先发（事件 > 遥测）
 * - 事件可靠下传：事件 TM 可要求地面回 TM-ACK（129/2），未收到会重传
 * - TC 接收：解析 TC 并回 Service 1 verification
 *
 * 传输层由上层注入 send_fn（可接 TCP/LoRa/串口等）。
 */

typedef uint8_t (*pus_link_send_fn_t)(const uint8_t* data, uint16_t len);
typedef void (*pus_link_cmd_handler_t)(const char* json_cmd);

/* Service 5（Event reporting）subtype: severity */
#define PUS5_EVENT_INFO 1
#define PUS5_EVENT_LOW 2
#define PUS5_EVENT_MEDIUM 3
#define PUS5_EVENT_HIGH 4

void PusLink_Init(pus_link_send_fn_t send_fn, uint16_t apid, uint16_t source_id, uint16_t dest_id);
void PusLink_SetConnected(uint8_t connected);
void PusLink_SetCommandHandler(pus_link_cmd_handler_t handler);

/* 输入：来自传输层的原始字节流（可能包含半包/多包） */
void PusLink_FeedBytes(const uint8_t* data, uint16_t len);

/* 入队：payload_json 必须是一个 JSON 对象字符串（以 '{' 开头、以 '}' 结尾），不含换行 */
uint8_t PusLink_QueueHousekeeping(const char* payload_json);
uint8_t PusLink_QueueEvent(uint8_t event_subtype, const char* payload_json, uint8_t ack_required);

/* 在主循环中周期调用：发送队列中待发消息（一次最多发一条） */
uint8_t PusLink_Poll(void);

#endif /* __PUS_LINK_H */

