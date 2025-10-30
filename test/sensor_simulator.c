/**
 ******************************************************************************
 * @file           : sensor_simulator.c
 * @brief          : 传感器模拟器 - 用于无硬件开发测试
 * @author         : 苏世鼎
 * @date           : 2025-10-04
 ******************************************************************************
 * 说明：这个文件可以在PC上编译运行，模拟传感器数据
 *      用于测试算法逻辑，不需要真实硬件
 ******************************************************************************
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include <math.h>

/* 模拟的传感器数据结构 */
typedef struct {
    float ch4_ppm;      // 甲烷浓度
    float co_ppm;       // 一氧化碳浓度
    float co2_ppm;      // 二氧化碳浓度
    float so2_ppm;      // 二氧化硫浓度
    float temperature;  // 温度
    float humidity;     // 湿度
    uint32_t timestamp; // 时间戳
} SensorData_t;

/* 气体类型枚举 */
typedef enum {
    GAS_BACKGROUND = 0,  // 背景气体
    GAS_CH4,            // 甲烷
    GAS_CO,             // 一氧化碳
    GAS_CO2,            // 二氧化碳
    GAS_MIXED,          // 混合气体
    GAS_UNKNOWN         // 未知
} GasType_t;

/* 函数声明 */
void Sensor_Init(void);
void Sensor_ReadAll(SensorData_t *data);
void Sensor_SimulateLeak(SensorData_t *data, GasType_t gas_type);
float Sensor_AddNoise(float value, float noise_level);
void Data_Filter(SensorData_t *data);
void Data_Print(SensorData_t *data);
GasType_t AI_Classify(SensorData_t *data);

/* 全局变量 */
static uint32_t sample_count = 0;

/**
 * @brief  初始化传感器（模拟）
 */
void Sensor_Init(void)
{
    srand(time(NULL));
    printf("========================================\n");
    printf("  星际嗅探者 - 传感器模拟器\n");
    printf("  Interstellar Sniffer Simulator v1.0\n");
    printf("  Developer: 苏世鼎\n");
    printf("========================================\n\n");
    printf("传感器初始化完成！\n\n");
}

/**
 * @brief  读取所有传感器数据（模拟）
 * @param  data: 传感器数据结构指针
 */
void Sensor_ReadAll(SensorData_t *data)
{
    // 模拟背景值（正常大气环境）
    data->ch4_ppm = 1.8 + Sensor_AddNoise(0, 0.1);       // 大气甲烷约1.8ppm
    data->co_ppm = 0.1 + Sensor_AddNoise(0, 0.05);       // 大气CO约0.1ppm
    data->co2_ppm = 400.0 + Sensor_AddNoise(0, 10.0);    // 大气CO2约400ppm
    data->so2_ppm = 0.001 + Sensor_AddNoise(0, 0.001);   // SO2痕量
    data->temperature = 25.0 + Sensor_AddNoise(0, 1.0);  // 室温25℃
    data->humidity = 50.0 + Sensor_AddNoise(0, 5.0);     // 湿度50%
    data->timestamp = sample_count++;
}

/**
 * @brief  模拟气体泄漏
 * @param  data: 传感器数据结构指针
 * @param  gas_type: 泄漏的气体类型
 */
void Sensor_SimulateLeak(SensorData_t *data, GasType_t gas_type)
{
    switch(gas_type) {
        case GAS_CH4:
            data->ch4_ppm += 150.0 + Sensor_AddNoise(0, 10.0);  // 甲烷泄漏浓度提高到150ppm
            break;
        case GAS_CO:
            data->co_ppm += 10.0 + Sensor_AddNoise(0, 1.0);   // CO泄漏
            break;
        case GAS_CO2:
            data->co2_ppm += 500.0 + Sensor_AddNoise(0, 50.0); // CO2升高
            break;
        case GAS_MIXED:
            data->ch4_ppm += 20.0;
            data->co_ppm += 5.0;
            data->co2_ppm += 200.0;
            break;
        default:
            break;
    }
}

/**
 * @brief  添加噪声（模拟真实传感器）
 * @param  value: 原始值
 * @param  noise_level: 噪声水平
 * @retval 加噪后的值
 */
float Sensor_AddNoise(float value, float noise_level)
{
    float noise = ((float)rand() / RAND_MAX - 0.5) * 2.0 * noise_level;
    return value + noise;
}

/**
 * @brief  数据滤波（简单移动平均）
 * @param  data: 传感器数据指针
 */
void Data_Filter(SensorData_t *data)
{
    static SensorData_t history[5] = {0};
    static int index = 0;

    // 保存当前数据
    history[index] = *data;
    index = (index + 1) % 5;

    // 计算均值
    float sum_ch4 = 0, sum_co = 0, sum_co2 = 0;
    for(int i = 0; i < 5; i++) {
        sum_ch4 += history[i].ch4_ppm;
        sum_co += history[i].co_ppm;
        sum_co2 += history[i].co2_ppm;
    }

    data->ch4_ppm = sum_ch4 / 5.0;
    data->co_ppm = sum_co / 5.0;
    data->co2_ppm = sum_co2 / 5.0;
}

/**
 * @brief  打印传感器数据
 * @param  data: 传感器数据指针
 */
void Data_Print(SensorData_t *data)
{
    printf("[%04u] ", data->timestamp);
    printf("CH4:%.2f ppm | ", data->ch4_ppm);
    printf("CO:%.2f ppm | ", data->co_ppm);
    printf("CO2:%.1f ppm | ", data->co2_ppm);
    printf("Temp:%.1f°C | ", data->temperature);
    printf("Humi:%.1f%%", data->humidity);
}

/**
 * @brief  简单的AI分类算法（规则基础）
 * @param  data: 传感器数据指针
 * @retval 气体类型
 */
GasType_t AI_Classify(SensorData_t *data)
{
    // 阈值判断（简化版AI）
    if(data->ch4_ppm > 10.0) {
        return GAS_CH4;
    }
    else if(data->co_ppm > 5.0) {
        return GAS_CO;
    }
    else if(data->co2_ppm > 800.0) {
        return GAS_CO2;
    }
    else if(data->ch4_ppm > 5.0 && data->co_ppm > 2.0) {
        return GAS_MIXED;
    }
    else {
        return GAS_BACKGROUND;
    }
}

/**
 * @brief  主程序
 */
int main(void)
{
    SensorData_t sensor_data;

    // 初始化
    Sensor_Init();

    printf("开始模拟测试...\n");
    printf("场景1: 正常背景环境（10次采样）\n");
    printf("---------------------------------------------------\n");

    // 场景1: 正常环境
    for(int i = 0; i < 10; i++) {
        Sensor_ReadAll(&sensor_data);
        Data_Filter(&sensor_data);
        Data_Print(&sensor_data);

        GasType_t gas_type = AI_Classify(&sensor_data);
        printf(" → %s\n", gas_type == GAS_BACKGROUND ? "背景气体" : "异常！");
    }

    printf("\n场景2: 检测到甲烷泄漏！\n");
    printf("---------------------------------------------------\n");

    // 场景2: 甲烷泄漏
    for(int i = 0; i < 10; i++) {
        Sensor_ReadAll(&sensor_data);
        Sensor_SimulateLeak(&sensor_data, GAS_CH4);  // 模拟泄漏
        Data_Filter(&sensor_data);
        Data_Print(&sensor_data);

        GasType_t gas_type = AI_Classify(&sensor_data);
        const char* gas_name[] = {"背景", "甲烷", "CO", "CO2", "混合", "未知"};
        printf(" → 检测到: %s", gas_name[gas_type]);

        if(gas_type == GAS_CH4) {
            printf(" ⚠️ 警告！");
        }
        printf("\n");
    }

    printf("\n场景3: 混合气体泄漏\n");
    printf("---------------------------------------------------\n");

    // 场景3: 混合气体
    for(int i = 0; i < 10; i++) {
        Sensor_ReadAll(&sensor_data);
        Sensor_SimulateLeak(&sensor_data, GAS_MIXED);
        Data_Filter(&sensor_data);
        Data_Print(&sensor_data);

        GasType_t gas_type = AI_Classify(&sensor_data);
        const char* gas_name[] = {"背景", "甲烷", "CO", "CO2", "混合", "未知"};
        printf(" → 检测到: %s\n", gas_name[gas_type]);
    }

    printf("\n========================================\n");
    printf("测试完成！总采样次数: %u\n", sample_count);
    printf("========================================\n");
    
    // 等待用户按键，防止窗口立即关闭
    printf("\n按任意键退出...\n");
    getchar();

    return 0;
}
