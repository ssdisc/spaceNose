# GPIO 引脚配置总结

## 📍 STM32F407ZGT6 引脚分配表

### 当前项目使用的所有 GPIO 引脚

| 引脚 | 功能 | 连接对象 | ADC通道 | 说明 |
|:---:|:---|:---|:---:|:---|
| **PA0** | ~~ADC1_IN0~~ | ~~原传感器~~ | ❌ | **已废弃，不再使用** |
| **PA1** | ADC1_IN1 | **MQ-3 酒精传感器** | ✅ | 通过分压电路连接 |
| **PA2** | USART2_TX | ESP8266 RX | - | WiFi通信 |
| **PA3** | USART2_RX | ESP8266 TX | - | WiFi通信 |
| **PA5** | ADC1_IN5 | 原有传感器 | ✅ | 保持兼容性 |
| **PA9** | USART1_TX | USB转TTL | - | 调试串口 |
| **PA10** | USART1_RX | USB转TTL | - | 调试串口 |
| **PF9** | GPIO_OUTPUT | 板载LED0 | - | 状态指示 |
| **PF10** | GPIO_OUTPUT | 板载LED1 | - | 状态指示 |

---

## 🔌 硬件连接方案（最终版）

### 1. 原有传感器（保持不变）

```
原有传感器 → PA5 (ADC1_IN5)
├─ 输出电压：0-3.3V（直连，无需分压）
└─ 用途：原有的电压监测
```

**代码中的使用：**
```c
// 在 main.c 中
uint16_t adc_ch5 = Read_ADC(ADC_CHANNEL_5);
float voltage_ch5 = ADC_to_Voltage(adc_ch5);
```

---

### 2. MQ-3 酒精传感器（新增）

```
MQ-3 传感器
├─ VCC → 开发板 JP3 的 VCC5 (5V供电)
├─ GND → 开发板 JP3 的 GND
└─ AO  → 分压电路 → PA1 (ADC1_IN1)
          │
          └→ 20kΩ → PA1 → 10kΩ → GND
             (5V降到3.3V)
```

**代码中的使用：**
```c
// 在 sensor_manager.c 中
#define MQ3_ADC_CHANNEL  ADC_CHANNEL_1  // PA1

SensorData_t* mq3_data = SensorManager_GetData(SENSOR_TYPE_MQ3_ALCOHOL);
printf("酒精浓度: %.2f ppm\n", mq3_data->concentration);
```

---

## 🔧 GPIO 配置代码（已修复）

### stm32f4xx_hal_msp.c

```c
void HAL_ADC_MspInit(ADC_HandleTypeDef* hadc)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if(hadc->Instance == ADC1)
    {
        /* 使能时钟 */
        __HAL_RCC_ADC1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();

        /* ADC1 GPIO配置
         * PA5 -> ADC1_IN5 (原有传感器通道)
         * PA1 -> ADC1_IN1 (MQ-3 酒精传感器)
         */
        GPIO_InitStruct.Pin = GPIO_PIN_5 | GPIO_PIN_1;
        GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
    }
}
```

**关键点：**
- ✅ 同时配置了 **PA1** 和 **PA5**
- ✅ 模式设置为 `GPIO_MODE_ANALOG`
- ✅ 无上拉/下拉电阻

---

## 📊 ADC 通道使用状态

| ADC通道 | GPIO | 状态 | 用途 |
|:---:|:---:|:---:|:---|
| ADC1_IN0 | PA0 | ❌ 未使用 | 已废弃 |
| ADC1_IN1 | PA1 | ✅ **使用中** | **MQ-3 酒精传感器** |
| ADC1_IN2 | PA2 | ❌ 占用 | USART2_TX |
| ADC1_IN3 | PA3 | ❌ 占用 | USART2_RX |
| ADC1_IN4 | PA4 | ⚪ 可用 | 预留扩展 |
| ADC1_IN5 | PA5 | ✅ **使用中** | **原有传感器** |
| ADC1_IN6 | PA6 | ⚪ 可用 | 预留扩展 |
| ADC1_IN7 | PA7 | ⚪ 可用 | 预留扩展 |

---

## 🎯 快速参考

### 你需要连接的引脚：

**MQ-3 传感器接线（最终确定）：**

```
┌─────────────────────────────────┐
│  开发板 JP3 接口                 │
├─────────────────────────────────┤
│  VCC5 (引脚7) → MQ-3 VCC        │
│  GND          → MQ-3 GND        │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  MQ-3 模拟输出                   │
├─────────────────────────────────┤
│  MQ-3 AO → 20kΩ电阻             │
│            ↓                     │
│          中间点 → PA1 (ADC1_IN1) │
│            ↓                     │
│          10kΩ电阻 → GND          │
└─────────────────────────────────┘
```

**原有传感器接线（如果有）：**
```
传感器输出 (0-3.3V) → PA5 (ADC1_IN5)
```

---

## ✅ 验证清单

在烧录固件前，请确认：

- [ ] MQ-3 VCC 连接到 JP3 的 VCC5
- [ ] MQ-3 GND 连接到 JP3 的 GND
- [ ] MQ-3 AO 通过分压电路连接到 **PA1**（不是 PA0！）
- [ ] 分压电路：20kΩ（上） + 10kΩ（下）
- [ ] 原有传感器（如果有）连接到 **PA5**
- [ ] 用万用表测试分压输出 < 3.3V

---

## 🔍 故障排查

### 如果 MQ-3 读数异常：

1. **检查 ADC 配置：**
   ```c
   // 在 sensor_manager.c 中应该是：
   #define MQ3_ADC_CHANNEL  ADC_CHANNEL_1  // PA1
   ```

2. **检查 GPIO 配置：**
   ```c
   // 在 stm32f4xx_hal_msp.c 中应该包含：
   GPIO_InitStruct.Pin = GPIO_PIN_5 | GPIO_PIN_1;
   ```

3. **检查硬件连接：**
   - 用万用表测量 PA1 引脚电压（应在 0-3.3V）
   - 确认分压电路正确

4. **检查供电：**
   - 测量 JP3 的 VCC5 引脚（应为 5V）
   - 确认 MQ-3 微热（说明加热器工作）

---

## 📝 Git 提交历史说明

### 提交 `2959dc5`（2025-12-10）

**改动：** 将 ADC 通道从 `ADC_CHANNEL_0` 改为 `ADC_CHANNEL_5`

**问题：** 但忘记修改 `stm32f4xx_hal_msp.c` 中的 GPIO 配置，仍然是 PA0

**现已修复：** GPIO 配置已更新为 PA5 + PA1

---

## 🚀 下一步

1. **编译固件：**
   ```bash
   # 在 PlatformIO 中点击 "√" 编译
   ```

2. **烧录固件：**
   ```bash
   # 点击 "→" 上传
   ```

3. **打开串口监视器：**
   ```bash
   # 波特率：115200
   # 应该看到 MQ-3 数据输出
   ```

4. **测试传感器：**
   - 用酒精棉球测试响应
   - 观察浓度数值变化

---

**创建日期：** 2025-12-12
**最后更新：** GPIO 配置已修复
**状态：** ✅ 准备烧录测试
