/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : 星际嗅探者 - 传感器主控程序
 * @author         : 苏世鼎
 * @date           : 2025-10-31
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"
#include <stdio.h>
#include <string.h>

/* Private variables */
UART_HandleTypeDef huart1;  // 调试串口
UART_HandleTypeDef huart2;  // ESP8266串口
ADC_HandleTypeDef hadc1;

/* Private function prototypes */
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_ADC1_Init(void);
void Error_Handler(void);

/* ESP8266相关函数 */
void ESP8266_SendCommand(const char* cmd);
HAL_StatusTypeDef ESP8266_ReceiveResponse(uint8_t* buffer, uint16_t size, uint32_t timeout);
void ESP8266_ClearBuffer(void);
uint8_t ESP8266_SendAndWaitOK(const char* cmd, uint32_t timeout);
uint8_t ESP8266_TestBaudRate(uint32_t baudrate);
void ESP8266_Test(void);
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password);
void ESP8266_GetIPAddress(void);
void ESP8266_ScanWiFi(void);

/**
 * @brief  重定向printf到UART1
 */
int _write(int file, char *ptr, int len)
{
    HAL_UART_Transmit(&huart1, (uint8_t*)ptr, len, HAL_MAX_DELAY);
    return len;
}

/**
 * @brief  读取ADC值
 */
uint16_t Read_ADC(uint32_t channel)
{
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = channel;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_15CYCLES;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 100);
    uint16_t adc_value = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    return adc_value;
}

/**
 * @brief  ADC转电压
 */
float ADC_to_Voltage(uint16_t adc_value)
{
    return (adc_value / 4096.0f) * 3.3f;
}

/**
 * @brief  主程序
 */
int main(void)
{
    /* 步骤1：初始化HAL库 */
    HAL_Init();
    
    /* 步骤2：配置系统时钟 */
    SystemClock_Config();

    /* 步骤3：初始化GPIO */
    MX_GPIO_Init();
    
    /* 步骤4：初始化UART */
    MX_USART1_UART_Init();
    MX_USART2_UART_Init();
    
    /* 步骤5：初始化ADC */
    MX_ADC1_Init();

    /* 等待串口稳定 */
    HAL_Delay(100);
    
    /* 打印启动信息 */
    printf("\r\n========================================\r\n");
    printf("  星际嗅探者 - 传感器系统启动\r\n");
    printf("  STM32F407ZGT6 @ %lu MHz\r\n", SystemCoreClock / 1000000);
    printf("  Developer: 苏世鼎\r\n");
    printf("========================================\r\n\r\n");

    /* 测试ESP8266连接 */
    printf("正在测试ESP8266连接...\r\n");
    ESP8266_Test();

    /* 连接WiFi热点 */
    printf("\r\n正在连接WiFi热点...\r\n");
    
    // ⚠️ 请在这里修改为你的笔记本WiFi热点名称和密码
    const char* wifi_ssid = "MCVC05LC";      // 修改为你的热点名称
    const char* wifi_password = "N46065rj";     // 修改为你的热点密码
    
    if (ESP8266_ConnectWiFi(wifi_ssid, wifi_password))
    {
        printf("\r\n✓ WiFi连接成功！\r\n");
        ESP8266_GetIPAddress();
    }
    else
    {
        printf("\r\n✗ WiFi连接失败，将继续运行但无网络功能\r\n");
    }
    
    printf("\r\n========================================\r\n");
    printf("系统初始化完成，进入主循环\r\n");
    printf("========================================\r\n\r\n");

    uint32_t counter = 0;

    /* 主循环 */
    while (1)
    {
        /* LED闪烁 */
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_9);
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_10);

        /* 读取传感器数据 */
        uint16_t adc_ch0 = Read_ADC(ADC_CHANNEL_0);
        float voltage_ch0 = ADC_to_Voltage(adc_ch0);

        /* 打印数据 */
        printf("[%lu] ADC_CH0: %u, Voltage: %.3f V\r\n",
               counter++, adc_ch0, voltage_ch0);

        /* 延时1秒 */
        HAL_Delay(1000);
    }
}

/**
 * @brief  系统时钟配置 - HSE 8MHz + PLL → 168MHz（最高性能）
 */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* 配置电源 */
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /* 配置HSE + PLL */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;      // HSE 8MHz ÷ 8 = 1MHz
    RCC_OscInitStruct.PLL.PLLN = 336;    // 1MHz × 336 = 336MHz
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;  // 336MHz ÷ 2 = 168MHz
    RCC_OscInitStruct.PLL.PLLQ = 7;      // 336MHz ÷ 7 = 48MHz (USB)
    
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }
    
    /* 配置系统时钟和总线分频 */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;     // 168MHz
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;      // 42MHz (APB1最大42MHz)
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;      // 84MHz (APB2最大84MHz)
    
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
    {
        Error_Handler();
    }
    
    /* 更新SystemCoreClock变量 */
    SystemCoreClockUpdate();
}

/**
 * @brief  GPIO初始化
 */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* 使能时钟 */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();

    /* 配置PF9和PF10（板载LED，低电平点亮） */
    GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);

    /* 初始状态：LED熄灭（高电平） */
    HAL_GPIO_WritePin(GPIOF, GPIO_PIN_9 | GPIO_PIN_10, GPIO_PIN_SET);
}

/**
 * @brief  USART1初始化 (PA9-TX, PA10-RX) - 调试串口
 */
static void MX_USART1_UART_Init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();

    huart1.Instance = USART1;
    huart1.Init.BaudRate = 9600;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    
    if (HAL_UART_Init(&huart1) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
 * @brief  USART2初始化 (PA2-TX, PA3-RX) - ESP8266串口
 */
static void MX_USART2_UART_Init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();

    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;  // ESP8266默认波特率
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    
    if (HAL_UART_Init(&huart2) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
 * @brief  ADC1初始化
 */
static void MX_ADC1_Init(void)
{
    __HAL_RCC_ADC1_CLK_ENABLE();

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    
    if (HAL_ADC_Init(&hadc1) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
 * @brief  发送AT指令到ESP8266
 */
void ESP8266_SendCommand(const char* cmd)
{
    printf("[发送] %s", cmd);
    HAL_UART_Transmit(&huart2, (uint8_t*)cmd, strlen(cmd), 1000);
}

/**
 * @brief  清空UART接收缓冲区
 */
void ESP8266_ClearBuffer(void)
{
    uint8_t dummy;
    // 清空所有待接收的数据
    while (HAL_UART_Receive(&huart2, &dummy, 1, 10) == HAL_OK);
}

/**
 * @brief  接收ESP8266响应（非阻塞式，逐字节接收）
 */
HAL_StatusTypeDef ESP8266_ReceiveResponse(uint8_t* buffer, uint16_t size, uint32_t timeout)
{
    uint16_t index = 0;
    uint32_t start_tick = HAL_GetTick();
    uint32_t last_receive_tick = HAL_GetTick();
    
    memset(buffer, 0, size);
    
    while (index < size - 1)
    {
        // 检查总超时
        if ((HAL_GetTick() - start_tick) > timeout)
        {
            if (index > 0)
            {
                return HAL_OK;  // 接收到部分数据
            }
            return HAL_TIMEOUT;  // 完全无响应
        }
        
        // 如果已经接收到数据，并且超过200ms没有新数据，认为接收完成
        if (index > 0 && (HAL_GetTick() - last_receive_tick) > 200)
        {
            return HAL_OK;
        }
        
        // 尝试接收单个字节
        if (HAL_UART_Receive(&huart2, &buffer[index], 1, 10) == HAL_OK)
        {
            index++;
            last_receive_tick = HAL_GetTick();
            
            // 如果收到OK或ERROR，再等待一小段时间确保完整
            if (index >= 2)
            {
                if (strstr((char*)buffer, "OK\r\n") || strstr((char*)buffer, "ERROR\r\n") || 
                    strstr((char*)buffer, "FAIL"))
                {
                    HAL_Delay(50);  // 等待可能的后续数据
                    // 尝试接收剩余数据
                    while ((index < size - 1) && 
                           (HAL_UART_Receive(&huart2, &buffer[index], 1, 20) == HAL_OK))
                    {
                        index++;
                    }
                    return HAL_OK;
                }
            }
        }
    }
    
    return HAL_OK;
}

/**
 * @brief  发送命令并等待OK响应
 * @return 1=成功收到OK, 0=失败
 */
uint8_t ESP8266_SendAndWaitOK(const char* cmd, uint32_t timeout)
{
    uint8_t buffer[256] = {0};
    
    // 清空缓冲区
    ESP8266_ClearBuffer();
    HAL_Delay(50);
    
    // 发送命令
    HAL_UART_Transmit(&huart2, (uint8_t*)cmd, strlen(cmd), 1000);
    HAL_Delay(100);
    
    // 接收响应
    ESP8266_ReceiveResponse(buffer, sizeof(buffer), timeout);
    
    // 检查是否包含OK
    if (strstr((char*)buffer, "OK"))
    {
        return 1;
    }
    
    return 0;
}

/**
 * @brief  测试指定波特率的ESP8266连接
 */
uint8_t ESP8266_TestBaudRate(uint32_t baudrate)
{
    uint8_t rx_buffer[128] = {0};
    HAL_StatusTypeDef status;
    
    printf("  测试波特率 %lu ... ", baudrate);
    
    // 重新配置USART2波特率
    huart2.Init.BaudRate = baudrate;
    if (HAL_UART_Init(&huart2) != HAL_OK)
    {
        printf("初始化失败\r\n");
        return 0;
    }
    
    // 清空接收缓冲区
    HAL_Delay(50);
    uint8_t dummy;
    while (HAL_UART_Receive(&huart2, &dummy, 1, 10) == HAL_OK);
    
    // 发送AT指令
    HAL_UART_Transmit(&huart2, (uint8_t*)"AT\r\n", 4, 1000);
    
    // 接收响应
    status = ESP8266_ReceiveResponse(rx_buffer, sizeof(rx_buffer), 1000);
    
    if (status == HAL_OK && strlen((char*)rx_buffer) > 0)
    {
        printf("成功！\r\n");
        printf("    响应: %s\r\n", rx_buffer);
        
        // 检查是否包含OK
        if (strstr((char*)rx_buffer, "OK"))
        {
            return 1;  // 成功
        }
    }
    else
    {
        printf("无响应\r\n");
    }
    
    return 0;
}

/**
 * @brief  测试ESP8266连接（增强版）
 */
void ESP8266_Test(void)
{
    printf("\r\n=== ESP8266 连接诊断 ===\r\n\r");
    
    // 常见的ESP8266波特率列表
    uint32_t baudrates[] = {115200, 9600, 57600, 74880, 38400, 19200};
    uint8_t baudrate_count = sizeof(baudrates) / sizeof(baudrates[0]);
    
    printf("开始自动检测ESP8266波特率...\r\n\r\n");
    
    for (uint8_t i = 0; i < baudrate_count; i++)
    {
        if (ESP8266_TestBaudRate(baudrates[i]))
        {
            printf("\r\n✓ ESP8266连接成功！波特率: %lu\r\n", baudrates[i]);
            printf("=========================\r\n\r\n");
            
            // 获取版本信息
            printf("正在获取ESP8266版本信息...\r\n");
            uint8_t version_buffer[256] = {0};
            HAL_UART_Transmit(&huart2, (uint8_t*)"AT+GMR\r\n", 8, 1000);
            HAL_Delay(200);
            ESP8266_ReceiveResponse(version_buffer, sizeof(version_buffer), 1500);
            printf("%s\r\n", version_buffer);
            
            return;
        }
    }
    
    printf("\r\n✗ 所有波特率测试失败！\r\n");
    printf("\r\n请检查以下问题：\r\n");
    printf("  1. ESP8266是否正确供电（3.3V，需要200-300mA电流）\r\n");
    printf("  2. TX/RX连接是否交叉（STM32 TX→ESP8266 RX, STM32 RX→ESP8266 TX）\r\n");
    printf("  3. 是否共地（GND连接）\r\n");
    printf("  4. ESP8266的CH_PD（使能）引脚是否接3.3V\r\n");
    printf("  5. 尝试按下ESP8266的复位按钮后重新测试\r\n");
    printf("=========================\r\n\r\n");
}

/**
 * @brief  扫描可用WiFi热点
 */
void ESP8266_ScanWiFi(void)
{
    uint8_t buffer[1024] = {0};
    
    printf("\r\n正在扫描附近的WiFi热点...\r\n");
    printf("（这可能需要几秒钟）\r\n\r\n");
    
    HAL_UART_Transmit(&huart2, (uint8_t*)"AT+CWLAP\r\n", 10, 1000);
    HAL_Delay(100);
    
    // 扫描需要较长时间
    ESP8266_ReceiveResponse(buffer, sizeof(buffer), 8000);
    
    if (strlen((char*)buffer) > 0)
    {
        printf("扫描结果:\r\n");
        printf("%s\r\n", buffer);
    }
    else
    {
        printf("未扫描到WiFi热点\r\n");
    }
}

/**
 * @brief  查询ESP8266的IP地址
 */
void ESP8266_GetIPAddress(void)
{
    uint8_t buffer[256] = {0};
    
    printf("\r\n正在查询IP地址...\r\n");
    
    HAL_UART_Transmit(&huart2, (uint8_t*)"AT+CIFSR\r\n", 10, 1000);
    HAL_Delay(200);
    ESP8266_ReceiveResponse(buffer, sizeof(buffer), 1500);
    
    printf("网络信息:\r\n%s\r\n", buffer);
}

/**
 * @brief  连接到WiFi热点
 * @param  ssid: WiFi热点名称
 * @param  password: WiFi密码
 * @return 1=成功, 0=失败
 */
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password)
{
    uint8_t buffer[512] = {0};
    char cmd[128] = {0};
    uint8_t retry_count = 0;
    
    printf("\r\n--- WiFi连接流程 ---\r\n\r\n");
    
    // 步骤0：确保ESP8266处于良好状态
    printf("0. 准备ESP8266...\r\n");
    ESP8266_ClearBuffer();
    HAL_Delay(500);
    
    // 发送AT测试
    if (ESP8266_SendAndWaitOK("AT\r\n", 1000))
    {
        printf("   ✓ ESP8266响应正常\r\n\r\n");
    }
    else
    {
        printf("   ⚠ ESP8266响应异常，尝试继续...\r\n\r\n");
    }
    
    // 步骤1：设置为Station模式
    printf("1. 设置为Station模式...\r\n");
    
    // 清空缓冲区并等待
    ESP8266_ClearBuffer();
    HAL_Delay(200);
    
    HAL_UART_Transmit(&huart2, (uint8_t*)"AT+CWMODE=1\r\n", 13, 1000);
    HAL_Delay(500);  // 增加延时，等待ESP8266处理
    
    memset(buffer, 0, sizeof(buffer));
    ESP8266_ReceiveResponse(buffer, sizeof(buffer), 3000);
    
    printf("   收到响应: [%s]\r\n", buffer);
    
    if (strstr((char*)buffer, "OK") || strstr((char*)buffer, "no change"))
    {
        printf("   ✓ 模式设置成功\r\n\r\n");
    }
    else
    {
        printf("   ⚠ 模式设置可能失败，但继续尝试...\r\n\r\n");
        // 不直接返回，尝试继续
        HAL_Delay(1000);
    }
    
    // 步骤2：断开之前的连接
    printf("2. 断开之前的连接...\r\n");
    ESP8266_ClearBuffer();
    HAL_Delay(200);
    
    HAL_UART_Transmit(&huart2, (uint8_t*)"AT+CWQAP\r\n", 10, 1000);
    HAL_Delay(500);
    
    memset(buffer, 0, sizeof(buffer));
    ESP8266_ReceiveResponse(buffer, sizeof(buffer), 2000);
    printf("   ✓ 已断开（或未连接）\r\n\r\n");
    
    // 步骤3：连接到指定WiFi（最多尝试2次）
    for (retry_count = 0; retry_count < 2; retry_count++)
    {
        if (retry_count > 0)
        {
            printf("\r\n正在重试连接（第%d次）...\r\n", retry_count + 1);
            HAL_Delay(2000);
        }
        
        printf("3. 连接到WiFi: %s\r\n", ssid);
        printf("   密码: %s\r\n", password);
        printf("   正在连接（最多25秒）...\r\n");
        
        // 清空缓冲区
        ESP8266_ClearBuffer();
        HAL_Delay(200);
        
        sprintf(cmd, "AT+CWJAP=\"%s\",\"%s\"\r\n", ssid, password);
        HAL_UART_Transmit(&huart2, (uint8_t*)cmd, strlen(cmd), 1000);
        HAL_Delay(1000);
        
        // 连接WiFi需要较长时间
        memset(buffer, 0, sizeof(buffer));
        ESP8266_ReceiveResponse(buffer, sizeof(buffer), 25000);
        
        printf("   收到响应: [%s]\r\n", buffer);
        
        // 检查是否连接成功
        if (strstr((char*)buffer, "WIFI GOT IP") || 
            (strstr((char*)buffer, "OK") && !strstr((char*)buffer, "FAIL")))
        {
            printf("   ✓ WiFi连接成功！\r\n");
            return 1;
        }
        else if (strstr((char*)buffer, "FAIL") || strstr((char*)buffer, "+CWJAP:"))
        {
            printf("   ✗ 连接失败\r\n");
            
            // 分析错误原因
            if (strstr((char*)buffer, "+CWJAP:1"))
                printf("   原因: 连接超时\r\n");
            else if (strstr((char*)buffer, "+CWJAP:2"))
                printf("   原因: 密码错误\r\n");
            else if (strstr((char*)buffer, "+CWJAP:3"))
                printf("   原因: 找不到目标AP\r\n");
            else if (strstr((char*)buffer, "+CWJAP:4"))
                printf("   原因: 连接失败\r\n");
            
            // 如果不是最后一次，继续重试
            if (retry_count < 1)
            {
                continue;
            }
        }
    }
    
    // 所有尝试都失败
    printf("\r\n   ✗ WiFi连接失败！\r\n");
    printf("   请检查：\r\n");
    printf("   - WiFi名称和密码是否正确\r\n");
    printf("   - 热点是否已开启\r\n");
    printf("   - 热点频段是否为2.4GHz\r\n");
    printf("   - ESP8266与热点的距离\r\n");
    return 0;
}

/**
 * @brief  错误处理 - 快速闪烁LED表示错误
 */
void Error_Handler(void)
{
    /* 确保GPIO时钟已使能 */
    __HAL_RCC_GPIOF_CLK_ENABLE();
    
    /* 配置GPIO（以防还没初始化） */
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);
    
    /* 快速闪烁表示错误 */
    while (1)
    {
        GPIOF->ODR ^= (GPIO_PIN_9 | GPIO_PIN_10);  // 翻转
        for(volatile uint32_t i = 0; i < 200000; i++);
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    printf("Assert failed: %s:%lu\r\n", file, line);
}
#endif
