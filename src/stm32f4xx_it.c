/**
 ******************************************************************************
 * @file    stm32f4xx_it.c
 * @brief   中断服务例程
 ******************************************************************************
 */

#include "stm32f4xx_hal.h"
#include "stm32f4xx_it.h"
#include "esp8266_driver.h"

// 从main.c中引用的句柄
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;

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

/******************************************************************************/
/*                 STM32F4xx Peripherals Interrupt Handlers                   */
/*  Add here the Interrupt Handlers for the used peripherals.                 */
/*    For the available peripheral interrupt handler names,                   */
/*    please refer to the startup file (startup_stm32f4xx.s).                 */
/******************************************************************************/

/**
  * @brief This function handles USART2 global interrupt.
  */
void USART2_IRQHandler(void)
{
  HAL_UART_IRQHandler(&huart2);
}

/**
  * @brief  Rx Transfer completed callback.
  * @param  huart: UART handle
  * @note   This function is executed when the reception of a single byte is complete.
  * @retval None
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  /* 判断是否是来自ESP8266的串口(USART2) */
  if (huart->Instance == USART2)
  {
    // 调用驱动中的回调函数, 将接收到的字节存入环形缓冲区
    ESP8266_RxCallback();
  }
}
