/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : 星际嗅探者 - 传感器主控程序
 * @author         : 苏世鼎
 * @date           : 2025-10-04
 ******************************************************************************
 * @attention
 *
 * 项目：星际嗅探者 (Interstellar Sniffer)
 * 功能：多气体传感器数据采集与智能识别
 *
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"
#include <stdio.h>
#include <string.h>

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;
ADC_HandleTypeDef hadc1;

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_ADC1_Init(void);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief  重定向printf到UART1
 */
int _write(int file, char *ptr, int len)
{
    HAL_UART_Transmit(&huart1, (uint8_t*)ptr, len, HAL_MAX_DELAY);
    return len;
}

/**
 * @brief  读取ADC值（传感器模拟量）
 * @param  channel: ADC通道号
 * @retval ADC原始值 (0-4095)
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
 * @brief  将ADC值转换为电压
 * @param  adc_value: ADC原始值
 * @retval 电压值(V)
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
    /* MCU配置 */
    HAL_Init();
    SystemClock_Config();

    /* 外设初始化 */
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_ADC1_Init();

    /* 启动信息 */
    printf("\r\n");
    printf("========================================\r\n");
    printf("  星际嗅探者 - 传感器系统启动\r\n");
    printf("  Interstellar Sniffer v1.0\r\n");
    printf("  Developer: 苏世鼎\r\n");
    printf("========================================\r\n");
    printf("\r\n");

    uint32_t counter = 0;

    /* 主循环 */
    while (1)
    {
        /* LED闪烁（心跳指示） - 测试多个可能的LED引脚 */
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_9);
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_10);
        HAL_GPIO_TogglePin(GPIOE, GPIO_PIN_0);
        HAL_GPIO_TogglePin(GPIOE, GPIO_PIN_1);

        /* 读取传感器数据 */
        uint16_t adc_ch0 = Read_ADC(ADC_CHANNEL_0);  // PA0 - 传感器1
        float voltage_ch0 = ADC_to_Voltage(adc_ch0);

        /* 打印数据 */
        printf("[%lu] ADC_CH0: %u, Voltage: %.3f V\r\n",
               counter++, adc_ch0, voltage_ch0);

        /* 延时1秒 */
        HAL_Delay(1000);
    }
}

/**
 * @brief  系统时钟配置
 *         配置为168MHz (STM32F407)
 */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* 使能HSE */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 7;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    /* 配置系统时钟 */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5);
}

/**
 * @brief  GPIO初始化
 */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* 使能GPIO时钟 */
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();

    /* 配置可能的LED引脚为输出 */
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    
    /* PC13 */
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
    
    /* PF9, PF10 */
    GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);
    
    /* PE0, PE1 */
    GPIO_InitStruct.Pin = GPIO_PIN_0 | GPIO_PIN_1;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* 初始状态：全部设为低电平 */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOF, GPIO_PIN_9 | GPIO_PIN_10, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_0 | GPIO_PIN_1, GPIO_PIN_RESET);
}

/**
 * @brief  USART1初始化 (PA9-TX, PA10-RX)
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
    HAL_UART_Init(&huart1);
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
    HAL_ADC_Init(&hadc1);
}

/**
 * @brief  错误处理函数
 */
void Error_Handler(void)
{
    __disable_irq();
    while (1)
    {
        // 错误指示：快速闪烁LED
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
        HAL_Delay(100);
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    printf("Assert failed: file %s on line %lu\r\n", file, line);
}
#endif
