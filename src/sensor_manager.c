/**
 ******************************************************************************
 * @file           : sensor_manager.c
 * @brief          : 传感器管理模块实现
 * @author         : SpaceNose Team
 * @date           : 2025-12-12
 * @version        : 1.0
 ******************************************************************************
 */

#include "sensor_manager.h"
#include <math.h>
#include <stdio.h>

/* 私有变量 */
static ADC_HandleTypeDef* g_hadc = NULL;
static MQ3_Config_t mq3_config = {0};

/* 全局传感器数据数组 */
SensorData_t g_sensor_data[SENSOR_TYPE_MAX] = {0};

/* MQ-3 校准参数 */
#define MQ3_RL_VALUE            10.0f   // 负载电阻 (kΩ)
#define MQ3_R0_CLEAN_AIR        60.0f   // 清洁空气中的R0基准值 (kΩ)
#define MQ3_PREHEAT_TIME_MS     180000  // 预热时间：3分钟（正式使用需20小时）
#define MQ3_ADC_CHANNEL         ADC_CHANNEL_5  // 使用PA5 (ADC1_CH5)

/* 电压分压比（根据你的硬件电路调整） */
#define VOLTAGE_DIVIDER_RATIO   2.5f    // 分压：5V → 2.0V (15kΩ + 10kΩ)
#define ADC_VREF                3.3f    // STM32参考电压
#define ADC_RESOLUTION          4096.0f // 12位ADC

/**
 * @brief  传感器管理器初始化
 * @param  hadc: ADC句柄
 */
void SensorManager_Init(ADC_HandleTypeDef* hadc)
{
    g_hadc = hadc;

    /* 初始化所有传感器数据 */
    for (int i = 0; i < SENSOR_TYPE_MAX; i++) {
        g_sensor_data[i].type = i;
        g_sensor_data[i].status = SENSOR_STATUS_NOT_READY;
    }

    /* 初始化MQ-3 */
    MQ3_Init(MQ3_ADC_CHANNEL);

    printf("[传感器管理器] 初始化完成\r\n");
}

/**
 * @brief  更新所有传感器数据（在主循环中定期调用）
 */
void SensorManager_Update(void)
{
    /* 更新MQ-3数据 */
    SensorData_t* mq3_data = &g_sensor_data[SENSOR_TYPE_MQ3_ALCOHOL];

    mq3_data->adc_raw = MQ3_ReadADC();
    mq3_data->voltage = MQ3_ReadVoltage();
    mq3_data->concentration = MQ3_ReadConcentration();
    mq3_data->timestamp = HAL_GetTick();

    /* 检查预热状态 */
    if (!mq3_config.is_preheated) {
        uint32_t elapsed = HAL_GetTick() - mq3_config.preheat_start_time;
        if (elapsed >= MQ3_PREHEAT_TIME_MS) {
            mq3_config.is_preheated = true;
            mq3_data->status = SENSOR_STATUS_OK;
            printf("[MQ-3] 预热完成！\r\n");
        } else {
            mq3_data->status = SENSOR_STATUS_PREHEATING;
        }
    } else {
        mq3_data->status = SENSOR_STATUS_OK;
    }
}

/**
 * @brief  获取指定类型传感器的数据
 * @param  type: 传感器类型
 * @retval 传感器数据指针
 */
SensorData_t* SensorManager_GetData(SensorType_t type)
{
    if (type >= SENSOR_TYPE_MAX) {
        return NULL;
    }
    return &g_sensor_data[type];
}

/**
 * @brief  检查传感器是否就绪
 */
bool SensorManager_IsReady(SensorType_t type)
{
    if (type >= SENSOR_TYPE_MAX) {
        return false;
    }
    return g_sensor_data[type].status == SENSOR_STATUS_OK;
}

/* ========== MQ-3 酒精传感器专用函数 ========== */

/**
 * @brief  MQ-3初始化
 * @param  adc_channel: ADC通道
 */
void MQ3_Init(uint32_t adc_channel)
{
    mq3_config.adc_channel = adc_channel;
    mq3_config.r0 = MQ3_R0_CLEAN_AIR;
    mq3_config.is_preheated = false;
    mq3_config.preheat_start_time = HAL_GetTick();

    printf("[MQ-3] 初始化成功，开始预热...\r\n");
    printf("[MQ-3] 预计预热时间: %d 秒\r\n", MQ3_PREHEAT_TIME_MS / 1000);
}

/**
 * @brief  读取MQ-3的ADC原始值
 * @retval ADC值 (0-4095)
 */
uint16_t MQ3_ReadADC(void)
{
    if (g_hadc == NULL) {
        return 0;
    }

    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = mq3_config.adc_channel;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES;  // 增加采样时间提高精度
    HAL_ADC_ConfigChannel(g_hadc, &sConfig);

    HAL_ADC_Start(g_hadc);
    HAL_ADC_PollForConversion(g_hadc, 100);
    uint16_t adc_value = HAL_ADC_GetValue(g_hadc);
    HAL_ADC_Stop(g_hadc);

    return adc_value;
}

/**
 * @brief  读取MQ-3的电压值
 * @retval 电压值 (V)
 */
float MQ3_ReadVoltage(void)
{
    uint16_t adc_raw = MQ3_ReadADC();

    /* ADC转电压 */
    float voltage = (adc_raw / ADC_RESOLUTION) * ADC_VREF;

    /* 如果使用了分压电路，需要还原真实电压 */
    voltage *= VOLTAGE_DIVIDER_RATIO;

    return voltage;
}

/**
 * @brief  计算传感器电阻Rs
 * @param  voltage: 传感器输出电压
 * @retval Rs (kΩ)
 */
static float MQ3_CalculateRs(float voltage)
{
    /* 公式：Rs = (Vc - Vout) * RL / Vout
     * Vc = 5V (传感器供电电压)
     * Vout = 测量到的电压
     * RL = 负载电阻
     */
    if (voltage <= 0.01f) {
        voltage = 0.01f;  // 防止除零
    }

    float rs = (5.0f - voltage) * MQ3_RL_VALUE / voltage;
    return rs;
}

/**
 * @brief  根据Rs/R0比值计算PPM浓度
 * @param  rs_r0_ratio: Rs/R0比值
 * @retval 酒精浓度 (ppm)
 *
 * @note   基于MQ-3数据手册的对数曲线拟合
 *         公式: ppm = A * (Rs/R0)^B
 *         对于MQ-3酒精检测: A ≈ 0.4, B ≈ -1.431
 */
float MQ3_CalculatePPM(float rs_r0_ratio)
{
    /* MQ-3酒精检测曲线参数（根据数据手册调整） */
    const float A = 0.4f;
    const float B = -1.431f;

    /* 计算浓度 */
    float ppm = A * powf(rs_r0_ratio, B);

    /* 限制范围 */
    if (ppm < 0) ppm = 0;
    if (ppm > 1000) ppm = 1000;

    return ppm;
}

/**
 * @brief  读取MQ-3的酒精浓度
 * @retval 酒精浓度 (ppm)
 */
float MQ3_ReadConcentration(void)
{
    float voltage = MQ3_ReadVoltage();
    float rs = MQ3_CalculateRs(voltage);
    float rs_r0_ratio = rs / mq3_config.r0;
    float ppm = MQ3_CalculatePPM(rs_r0_ratio);

    return ppm;
}

/**
 * @brief  校准MQ-3传感器（在清洁空气中校准R0）
 * @note   需要在清洁空气环境中调用此函数
 */
void MQ3_Calibrate(void)
{
    printf("[MQ-3] 开始校准，请确保传感器处于清洁空气中...\r\n");

    /* 多次采样取平均 */
    const int samples = 50;
    float sum_rs = 0;

    for (int i = 0; i < samples; i++) {
        float voltage = MQ3_ReadVoltage();
        float rs = MQ3_CalculateRs(voltage);
        sum_rs += rs;
        HAL_Delay(100);
    }

    mq3_config.r0 = sum_rs / samples;

    printf("[MQ-3] 校准完成！R0 = %.2f kΩ\r\n", mq3_config.r0);
}
