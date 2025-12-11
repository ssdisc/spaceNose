/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : 星际嗅探者 - 传感器主控程序
 * @author         : 苏世鼎
 * @date           : 2025-10-31
 * @version        : 2.0 (中断驱动版)
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include "esp8266_driver.h" // 引入新的ESP8266驱动

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

/* 新的ESP8266相关函数 */
uint8_t ESP8266_Test(void);
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password);
void ESP8266_GetIPAddress(void);

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

    /* 步骤6: 初始化ESP8266驱动 (关键改动) */
    ESP8266_Init();

    /* 等待串口稳定 */
    HAL_Delay(1000);
    
    /* 打印启动信息 */
    printf("\r\n========================================\r\n");
    printf("  星际嗅探者 - 传感器系统启动 (v2.0)\r\n");
    printf("  STM32F407ZGT6 @ %lu MHz\r\n", SystemCoreClock / 1000000);
    printf("  Developer: 苏世鼎\r\n");
    printf("========================================\r\n\r\n");

    /* 测试ESP8266连接 */
    uint8_t udp_enabled = 0;  // UDP连接状态标志
    printf("正在测试ESP8266连接...\r\n");
    if (ESP8266_Test())
    {
        /* 连接WiFi热点 */
        printf("\r\n正在连接WiFi热点...\r\n");
        
        // ⚠️ 请在这里修改为你的笔记本WiFi热点名称和密码
        const char* wifi_ssid = "MCVC05LC";      // 修改为你的热点名称
        const char* wifi_password = "N46065rj";     // 修改为你的热点密码
        
        if (ESP8266_ConnectWiFi(wifi_ssid, wifi_password))
        {
            printf("\r\n✓ WiFi连接成功！\r\n");
            ESP8266_GetIPAddress();
            
            /* 建立UDP连接到电脑服务器 */
            printf("\r\n正在建立UDP连接...\r\n");
            // ⚠️ 请修改为你电脑的IP地址（打开WiFi热点后，电脑会自动获得一个IP，通常是192.168.137.1）
            const char* server_ip = "192.168.137.1";  // 电脑WiFi热点的IP地址
            uint16_t server_port = 8888;              // UDP服务器端口
            uint16_t local_port = 5555;               // ESP8266本地端口
            
            if (ESP8266_StartConnection("UDP", server_ip, server_port, local_port))
            {
                printf("\r\n✓ UDP连接建立成功！\r\n");
                udp_enabled = 1;
            }
            else
            {
                printf("\r\n✗ UDP连接失败，将只本地显示数据\r\n");
            }
        }
        else
        {
            printf("\r\n✗ WiFi连接失败，将继续运行但无网络功能\r\n");
        }
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
        uint16_t adc_ch5 = Read_ADC(ADC_CHANNEL_5);
        float voltage_ch5 = ADC_to_Voltage(adc_ch5);

        /* 打印数据 */
        printf("[%lu] ADC_CH5: %u, Voltage: %.3f V\r\n",
               counter++, adc_ch5, voltage_ch5);

        /* 如果UDP已连接，发送数据到服务器 */
        if (udp_enabled)
        {
            // 构建JSON格式的数据
            char json_data[128] = {0};
            sprintf(json_data, "{\"counter\":%lu,\"adc\":%u,\"voltage\":%.3f}\n",
                    counter - 1, adc_ch5, voltage_ch5);
            
            // 通过UDP发送
            if (!ESP8266_SendUDP((uint8_t*)json_data, strlen(json_data)))
            {
                printf("   [警告] UDP发送失败\r\n");
            }
        }

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
    huart1.Init.BaudRate = 115200;
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
    hadc1.Init.ContinuousConvMode = ENABLE;
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
 * @brief  测试ESP8266连接 (重构后)
 * @return 1: 成功; 0: 失败
 */
uint8_t ESP8266_Test(void)
{
    printf("\r\n=== ESP8266 连接诊断 ===\r\n");
    
    if (ESP8266_SendAndWaitOK("AT\r\n", 2000))
    {
        printf("✓ ESP8266响应正常！\r\n");
        printf("=========================\r\n\r\n");
        
        // 获取版本信息
        printf("正在获取ESP8266版本信息...\r\n");
        ESP8266_ClearBuffer();
        ESP8266_SendCommand("AT+GMR\r\n");
        if(ESP8266_WaitForString("OK", 2000)) {
            // 响应已在 WaitForString 内部打印
        }
        return 1;
    }
    else
    {
        printf("\r\n✗ ESP8266无响应！\r\n");
        printf("\r\n请检查以下问题：\r\n");
        printf("  1. ESP8266是否正确供电（3.3V，需要200-300mA电流）\r\n");
        printf("  2. TX/RX连接是否交叉（STM32 TX→ESP8266 RX, STM32 RX→ESP8266 TX）\r\n");
        printf("  3. 是否共地（GND连接）\r\n");
        printf("  4. ESP8266的CH_PD（使能）引脚是否接3.3V\r\n");
        printf("  5. 尝试按下ESP8266的复位按钮后重新测试\r\n");
        printf("=========================\r\n\r\n");
        return 0;
    }
}

/**
 * @brief  查询ESP8266的IP地址 (重构后)
 */
void ESP8266_GetIPAddress(void)
{
    printf("\r\n正在查询IP地址...\r\n");
    ESP8266_ClearBuffer();
    ESP8266_SendCommand("AT+CIFSR\r\n");
    if(ESP8266_WaitForString("OK", 5000)) {
        // 响应已在 WaitForString 内部打印
    }
}

/**
 * @brief  连接到WiFi热点 (重构后)
 * @return 1=成功, 0=失败
 */
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password)
{
    char cmd[128] = {0};
    
    printf("\r\n--- WiFi连接流程 ---\r\n\r\n");
    
    // 步骤1：设置为Station模式
    printf("1. 设置为Station模式...\r\n");
    if (!ESP8266_SendAndWaitOK("AT+CWMODE=1\r\n", 5000)) {
        printf("   ⚠ 模式设置失败，但继续尝试...\r\n\r\n");
    } else {
        printf("   ✓ 模式设置成功\r\n\r\n");
    }
    HAL_Delay(1000);

    // 步骤2：断开之前的连接 (可选但推荐)
    printf("2. 断开之前的连接...\r\n");
    ESP8266_SendAndWaitOK("AT+CWQAP\r\n", 3000);
    printf("   ✓ 已断开（或未连接）\r\n\r\n");
    HAL_Delay(1000);

    // 步骤3：连接到指定WiFi
    printf("3. 连接到WiFi: %s\r\n", ssid);
    printf("   密码: %s\r\n", password);
    printf("   正在连接（最多25秒）...\r\n");
    
    sprintf(cmd, "AT+CWJAP=\"%s\",\"%s\"\r\n", ssid, password);
    
    ESP8266_ClearBuffer();
    ESP8266_SendCommand(cmd);
    
    // 等待 "WIFI GOT IP" 或 "OK"
    if (ESP8266_WaitForString("WIFI GOT IP", 25000) || ESP8266_WaitForString("OK", 1000))
    {
        printf("   ✓ WiFi连接成功！\r\n");
        return 1;
    }
    else
    {
        printf("\r\n   ✗ WiFi连接失败！\r\n");
        printf("   请检查：\r\n");
        printf("   - WiFi名称和密码是否正确\r\n");
        printf("   - 热点是否已开启\r\n");
        printf("   - 热点频段是否为2.4GHz\r\n");
        printf("   - ESP8266与热点的距离\r\n");
        return 0;
    }
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
