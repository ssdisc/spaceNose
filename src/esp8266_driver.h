#ifndef __ESP8266_DRIVER_H
#define __ESP8266_DRIVER_H

#include "stm32f4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

// 宏定义
#define ESP8266_RX_BUFFER_SIZE 1024 // 环形缓冲区大小, 1KB

// 外部变量声明
extern UART_HandleTypeDef huart2;

/**
 * @brief 初始化ESP8266驱动
 * @note  此函数会启动UART的循环接收中断
 */
void ESP8266_Init(void);

/**
 * @brief 清空接收缓冲区
 */
void ESP8266_ClearBuffer(void);

/**
 * @brief 向ESP8266发送命令
 * @param cmd 要发送的AT指令字符串 (需要以\r\n结尾)
 */
void ESP8266_SendCommand(const char* cmd);

/**
 * @brief 等待并检查响应中是否包含特定字符串
 * @param target 目标字符串, 例如 "OK", "FAIL", "WIFI GOT IP"
 * @param timeout 等待的超时时间 (毫秒)
 * @return 1: 找到目标字符串; 0: 超时或未找到
 */
uint8_t ESP8266_WaitForString(const char* target, uint32_t timeout);


/**
 * @brief 发送命令并等待OK响应
 * @param cmd 要发送的AT指令 (需要以\r\n结尾)
 * @param timeout 等待超时时间 (毫秒)
 * @return 1: 成功收到OK; 0: 失败
 */
uint8_t ESP8266_SendAndWaitOK(const char* cmd, uint32_t timeout);

/**
 * @brief 获取当前接收缓冲区中的所有内容
 * @param buffer 用于存放数据的缓冲区
 * @param buffer_size 缓冲区大小
 * @return 读取到的字节数
 */
uint16_t ESP8266_GetBuffer(char* buffer, uint16_t buffer_size);


/**
 * @brief UART接收回调函数，在 stm32f4xx_it.c 中被调用
 * @note  此函数是驱动的核心，处理收到的每一个字节
 */
void ESP8266_RxCallback(void);

/**
 * @brief 建立UDP连接
 * @param type "UDP" 或 "TCP"
 * @param remote_ip 远程服务器IP地址
 * @param remote_port 远程服务器端口
 * @param local_port 本地端口（UDP模式下需要）
 * @return 1: 成功; 0: 失败
 */
uint8_t ESP8266_StartConnection(const char* type, const char* remote_ip, uint16_t remote_port, uint16_t local_port);

/**
 * @brief 通过UDP发送数据
 * @param data 要发送的数据
 * @param len 数据长度
 * @return 1: 成功; 0: 失败
 */
uint8_t ESP8266_SendUDP(const uint8_t* data, uint16_t len);

/**
 * @brief 设置透传模式
 * @param enable 1: 启用透传; 0: 退出透传
 * @return 1: 成功; 0: 失败
 */
uint8_t ESP8266_SetTransparentMode(uint8_t enable);

#endif /* __ESP8266_DRIVER_H */