# MySQL 数据库快速配置指南

## 🚀 3分钟快速配置

### 步骤 1: 安装 MySQL

如果还没安装 MySQL，请先下载安装：
- **下载地址**: https://dev.mysql.com/downloads/mysql/
- 安装过程中记住设置的 root 密码

### 步骤 2: 配置数据库连接

编辑 `backend/.env` 文件（如果不存在则手动创建）：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=spacenose

UDP_HOST=0.0.0.0
UDP_PORT=8888
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 步骤 3: 初始化数据库

在项目根目录运行：

```bash
cd backend
python init_database.py
```

看到以下输出表示成功：
```
✓ 数据库 'spacenose' 创建成功或已存在
✓ 数据库表创建成功
✅ 数据库初始化完成！
```

### 步骤 4: 启动服务器

```bash
cd backend
python main.py
```

看到以下输出表示数据库连接成功：
```
✓ 数据库连接成功: spacenose
✓ HTTP服务: http://127.0.0.1:8000
```

## ✅ 验证数据库是否工作

### 方法 1: 使用 API 接口

启动服务器后，访问：
```
http://localhost:8000/api/stats
```

### 方法 2: 查看 MySQL

```bash
mysql -u root -p
USE spacenose;
SELECT COUNT(*) FROM sensor_data;
```

## 🔧 常见问题解决

### 问题 1: 找不到 .env 文件

**解决**: 手动创建 `backend/.env` 文件，复制上面的配置内容

### 问题 2: 数据库连接失败

**检查清单**:
- [ ] MySQL 服务是否已启动？
- [ ] `.env` 中的密码是否正确？
- [ ] 端口 3306 是否被占用？

**Windows 检查 MySQL 服务**:
```powershell
# 检查服务状态
Get-Service MySQL*

# 启动服务
Start-Service MySQL80  # 服务名可能不同
```

### 问题 3: 权限错误

如果出现权限问题，在 MySQL 中执行：

```sql
GRANT ALL PRIVILEGES ON spacenose.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

## 📊 数据库表结构

系统会自动创建 `sensor_data` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键（自增） |
| counter | INT | 数据计数 |
| adc | INT | ADC值 |
| voltage | FLOAT | 电压值 |
| timestamp | DATETIME | 时间戳 |
| source_ip | VARCHAR(50) | 来源IP |

## 🎯 下一步

数据库配置完成后：

1. 确保 STM32 和 ESP8266 正常运行
2. 访问 `http://localhost:8000` 查看实时数据
3. 访问 `http://localhost:8000/docs` 查看完整 API 文档
4. 使用 `/api/data/recent` 等接口查询历史数据

---

**详细文档**: 参考 `数据库使用说明.md`

