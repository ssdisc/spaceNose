/**
 ******************************************************************************
 * @file    stm32f4xx_it.c
 * @brief   中断服务例程
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"
#include "stm32f4xx_it.h"

/**
 * @brief  NMI中断处理
 */
void NMI_Handler(void)
{
}

/**
 * @brief  硬件错误中断处理
 */
void HardFault_Handler(void)
{
    while (1)
    {
    }
}

/**
 * @brief  内存管理中断处理
 */
void MemManage_Handler(void)
{
    while (1)
    {
    }
}

/**
 * @brief  总线错误中断处理
 */
void BusFault_Handler(void)
{
    while (1)
    {
    }
}

/**
 * @brief  用法错误中断处理
 */
void UsageFault_Handler(void)
{
    while (1)
    {
    }
}

/**
 * @brief  SVC中断处理
 */
void SVC_Handler(void)
{
}

/**
 * @brief  调试监视器中断处理
 */
void DebugMon_Handler(void)
{
}

/**
 * @brief  PendSV中断处理
 */
void PendSV_Handler(void)
{
}

/**
 * @brief  SysTick中断处理
 */
void SysTick_Handler(void)
{
    HAL_IncTick();
}
