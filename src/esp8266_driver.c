#include "esp8266_driver.h"

// ----------------- 环形缓冲区实现 -----------------

/**
 * @brief 定义环形缓冲区结构体
 */
typedef struct {
    uint8_t buffer[ESP8266_RX_BUFFER_SIZE];
    volatile uint16_t head; // 写入指针
    volatile uint16_t tail; // 读取指针
} RingBuffer_t;

// 声明并初始化环形缓冲区
static RingBuffer_t rx_buffer = {{0}, 0, 0};

// 声明一个单字节的接收缓冲区, 用于中断接收
static uint8_t uart_rx_byte; 

// ----------------- 驱动核心函数 -----------------

/**
 * @brief 初始化ESP8266驱动, 启动中断接收
 */
void ESP8266_Init(void) {
    // 清空环形缓冲区
    ESP8266_ClearBuffer();
    // 启动UART的循环接收中断, 每次只接收一个字节
    // 当一个字节接收完成后, 会触发 HAL_UART_RxCpltCallback
    HAL_UART_Receive_IT(&huart2, &uart_rx_byte, 1);
}

/**
 * @brief UART接收完成回调函数 (在 stm32f4xx_it.c 中被调用)
 * @note  这是中断处理的核心部分
 */
void ESP8266_RxCallback(void) {
    // 计算下一个写入位置
    uint16_t next_head = (rx_buffer.head + 1) % ESP8266_RX_BUFFER_SIZE;

    // 检查缓冲区是否已满 (写入指针追上读取指针)
    if (next_head != rx_buffer.tail) {
        // 将接收到的字节存入环形缓冲区
        rx_buffer.buffer[rx_buffer.head] = uart_rx_byte;
        // 移动写入指针
        rx_buffer.head = next_head;
    }
    // else: 缓冲区已满, 丢弃这个字节 (在实际应用中可以增加错误计数)

    // 再次启动中断, 准备接收下一个字节
    HAL_UART_Receive_IT(&huart2, &uart_rx_byte, 1);
}

/**
 * @brief 清空环形缓冲区
 */
void ESP8266_ClearBuffer(void) {
    // 通过将头尾指针设为相同来清空缓冲区
    rx_buffer.head = 0;
    rx_buffer.tail = 0;
    // 可选: 清零物理内存
    memset((void*)rx_buffer.buffer, 0, ESP8266_RX_BUFFER_SIZE);
}

/**
 * @brief 向ESP8266发送命令
 */
void ESP8266_SendCommand(const char* cmd) {
    // 通过调试串口打印发送的命令
    printf("[发送] %s", cmd);
    // 通过UART2将命令发送给ESP8266
    HAL_UART_Transmit(&huart2, (uint8_t*)cmd, strlen(cmd), 1000);
}

/**
 * @brief 从环形缓冲区读取数据, 直到找到目标字符串或超时
 */
uint8_t ESP8266_WaitForString(const char* target, uint32_t timeout) {
    char temp_buf[ESP8266_RX_BUFFER_SIZE] = {0};
    uint16_t current_len = 0;
    uint32_t start_tick = HAL_GetTick();

    while ((HAL_GetTick() - start_tick) < timeout) {
        // 检查环形缓冲区是否有新数据
        while (rx_buffer.tail != rx_buffer.head) {
            // 从环形缓冲区取出一个字节
            char c = rx_buffer.buffer[rx_buffer.tail];
            rx_buffer.tail = (rx_buffer.tail + 1) % ESP8266_RX_BUFFER_SIZE;

            // 将取出的字节存入临时缓冲区
            if (current_len < sizeof(temp_buf) - 1) {
                temp_buf[current_len++] = c;
            }

            // 检查临时缓冲区中是否包含目标字符串
            if (strstr(temp_buf, target)) {
                // 为了调试, 打印收到的完整响应
                printf("[响应] %s\r\n", temp_buf);
                return 1; // 找到了
            }
        }
        // 短暂延时, 避免CPU空转
        HAL_Delay(1);
    }
    
    // 超时, 打印已收到的数据以供调试
    if(current_len > 0) {
        printf("[超时响应] %s\r\n", temp_buf);
    } else {
        printf("[超时] 未收到任何响应\r\n");
    }

    return 0; // 超时未找到
}

/**
 * @brief 发送命令并等待"OK"
 */
uint8_t ESP8266_SendAndWaitOK(const char* cmd, uint32_t timeout) {
    ESP8266_ClearBuffer();
    ESP8266_SendCommand(cmd);
    return ESP8266_WaitForString("OK", timeout);
}

/**
 * @brief 获取当前接收缓冲区中的所有内容
 */
uint16_t ESP8266_GetBuffer(char* buffer, uint16_t buffer_size) {
    uint16_t len = 0;
    // 确保传入的buffer足够大
    if (buffer == NULL || buffer_size == 0) {
        return 0;
    }

    // 简单的数据复制, 在这个应用场景下暂时不加锁
    while (rx_buffer.tail != rx_buffer.head && len < buffer_size - 1) {
        buffer[len++] = rx_buffer.buffer[rx_buffer.tail];
        rx_buffer.tail = (rx_buffer.tail + 1) % ESP8266_RX_BUFFER_SIZE;
    }
    
    buffer[len] = '\0'; // 添加字符串结束符
    return len;
}