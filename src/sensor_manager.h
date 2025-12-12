/**
 ******************************************************************************
 * @file           : sensor_manager.h
 * @brief          : 传感器管理模块头文件
 * @author         : SpaceNose Team
 * @date           : 2025-12-12
 * @version        : 1.0
 ******************************************************************************
 * @description    : 支持多种气体传感器的统一管理接口
 *                   - MQ-3 酒精传感器
 *                   - 可扩展其他MQ系列传感器
 ******************************************************************************
 */

#ifndef __SENSOR_MANAGER_H
#define __SENSOR_MANAGER_H

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* 传感器类型枚举 */
typedef enum {
    SENSOR_TYPE_MQ3_ALCOHOL = 0,  // MQ-3 酒精传感器
    SENSOR_TYPE_TEMPERATURE,      // 温度传感器（预留）
    SENSOR_TYPE_HUMIDITY,         // 湿度传感器（预留）
    SENSOR_TYPE_MAX               // 传感器数量
} SensorType_t;

/* 传感器状态 */
typedef enum {
    SENSOR_STATUS_OK = 0,         // 正常
    SENSOR_STATUS_PREHEATING,     // 预热中
    SENSOR_STATUS_ERROR,          // 错误
    SENSOR_STATUS_NOT_READY       // 未就绪
} SensorStatus_t;

/* 传感器数据结构 */
typedef struct {
    SensorType_t type;            // 传感器类型
    uint16_t adc_raw;             // ADC原始值 (0-4095)
    float voltage;                // 电压值 (V)
    float concentration;          // 气体浓度 (ppm)
    uint32_t timestamp;           // 时间戳 (ms)
    SensorStatus_t status;        // 状态
} SensorData_t;

/* MQ-3 传感器配置 */
typedef struct {
    uint32_t adc_channel;         // ADC通道 (ADC_CHANNEL_x)
    float r0;                     // 传感器在清洁空气中的基准电阻 (kΩ)
    bool is_preheated;            // 是否已预热
    uint32_t preheat_start_time;  // 预热开始时间
} MQ3_Config_t;

/* 公共API */
void SensorManager_Init(ADC_HandleTypeDef* hadc);
void SensorManager_Update(void);
SensorData_t* SensorManager_GetData(SensorType_t type);
bool SensorManager_IsReady(SensorType_t type);

/* MQ-3 专用API */
void MQ3_Init(uint32_t adc_channel);
uint16_t MQ3_ReadADC(void);
float MQ3_ReadVoltage(void);
float MQ3_ReadConcentration(void);
float MQ3_CalculatePPM(float rs_r0_ratio);
void MQ3_Calibrate(void);

/* 全局变量声明 */
extern SensorData_t g_sensor_data[SENSOR_TYPE_MAX];

#endif /* __SENSOR_MANAGER_H */
