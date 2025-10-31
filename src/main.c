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
UART_HandleTypeDef huart1;
ADC_HandleTypeDef hadc1;

/* Private function prototypes */
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_ADC1_Init(void);
void Error_Handler(void);

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
 * @brief  系统时钟配置 - 使用HSI 16MHz（最稳定的配置）
 */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* 配置电源 */
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /* 使用HSI内部时钟（16MHz），这是最可靠的选择 */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
    
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }
    
    /* 配置系统时钟 */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;     // 16MHz
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;      // 16MHz
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;      // 16MHz
    
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
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
 * @brief  USART1初始化 (PA9-TX, PA10-RX)
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
