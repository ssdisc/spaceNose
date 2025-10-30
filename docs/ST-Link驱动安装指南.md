# ST-Link驱动安装指南

## 问题现象
```
Error: open failed
in procedure 'program'
** OpenOCD init failed **
```

## 解决方法

### 方法1：使用Zadig安装驱动（推荐）

1. **下载Zadig**
   - 访问：https://zadig.akeo.ie/
   - 下载最新版本

2. **安装驱动**
   - 连接ST-Link到电脑
   - 运行Zadig
   - 点击菜单 `Options` → `List All Devices`
   - 在下拉列表中选择 `STM32 STLink` 或 `ST-Link Debug`
   - 驱动选择 `WinUSB` 或 `libusb-win32`
   - 点击 `Replace Driver` 或 `Install Driver`

3. **验证**
   ```bash
   C:\Users\25379\.platformio\penv\Scripts\platformio.exe device list
   ```

### 方法2：安装ST官方驱动

1. **下载ST-Link驱动**
   - 访问：https://www.st.com/zh/development-tools/stsw-link009.html
   - 或搜索 "STSW-LINK009"
   - 下载并安装

2. **重启电脑**

3. **重新连接ST-Link**

### 方法3：使用STM32CubeProgrammer

1. 下载安装 STM32CubeProgrammer
2. 连接ST-Link，尝试在CubeProgrammer中连接
3. 它会自动提示安装/更新驱动

## 硬件连接检查

### ST-Link与STM32的连接（SWD接口）
```
ST-Link      →      STM32F407ZG
---------------------------------
SWDIO        →      PA13 (SWDIO)
SWCLK        →      PA14 (SWCLK)
GND          →      GND
3.3V         →      3.3V (可选)
```

### 检查清单
- [ ] ST-Link USB线连接到电脑
- [ ] ST-Link指示灯亮起
- [ ] 4根杜邦线连接牢固
- [ ] STM32板子已上电
- [ ] 跳线帽设置正确（BOOT0接GND）

## 常见问题

### 1. "Error: open failed"
- **原因**：驱动未安装或ST-Link未连接
- **解决**：按上述方法安装驱动

### 2. "Error: target not found"
- **原因**：硬件连接问题
- **解决**：检查SWDIO、SWCLK连接

### 3. "Error: init mode failed"
- **原因**：芯片被锁定或供电不足
- **解决**：检查供电，尝试全片擦除

### 4. ST-Link固件版本过旧
运行ST-Link固件升级工具（STLinkUpgrade.exe）

## 其他上传方式

如果ST-Link一直有问题，可以尝试：

### 使用串口烧录（UART）
修改 `platformio.ini`：
```ini
upload_protocol = serial
upload_port = COM3  ; 改成你的串口号
```

注意：需要将BOOT0接3.3V，复位后进入bootloader模式

### 使用DFU（USB）
如果板子支持USB DFU：
```ini
upload_protocol = dfu
```
