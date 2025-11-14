# 🗄️ MySQL 数据库集成完成

## 📢 更新公告

**星际嗅探者**项目已成功集成 MySQL 数据库！现在系统支持：

✅ **数据持久化** - 所有传感器数据自动保存到数据库  
✅ **历史查询** - 通过 REST API 查询任意时间段的历史数据  
✅ **数据分析** - 支持统计、趋势分析等高级功能  
✅ **长期存储** - 数据永久保存，不受服务器重启影响  

---

## 🎯 新增功能

### 1. 数据自动保存
- UDP 接收到的每条数据都会自动保存到 MySQL
- 记录信息包括：计数、ADC值、电压、时间戳、来源IP
- 保存失败不影响实时显示功能

### 2. 历史数据查询 API
提供 7 个 REST API 接口：

| 接口 | 功能 |
|------|------|
| `GET /api/data/recent?limit=100` | 获取最近N条记录 |
| `GET /api/data/hours?hours=1` | 获取最近N小时数据 |
| `GET /api/data/range?start=...&end=...` | 时间范围查询 |
| `GET /api/data/{id}` | 根据ID查询 |
| `GET /api/stats` | 统计信息 |
| `DELETE /api/data/cleanup?days=30` | 清理旧数据 |
| `GET /api/latest` | 实时最新数据 |

### 3. 配置化管理
- 通过 `.env` 文件配置数据库连接
- 支持自定义数据库主机、端口、用户名、密码
- 配置与代码分离，更安全

### 4. 完善的工具支持
- **初始化脚本** - 一键创建数据库和表
- **测试脚本** - 快速诊断连接问题
- **示例代码** - 演示如何使用API
- **详细文档** - 中文文档，易于理解

---

## 🚀 快速开始（5分钟配置）

### 步骤 1: 安装 MySQL
如未安装，请下载：https://dev.mysql.com/downloads/mysql/

### 步骤 2: 配置数据库
编辑 `backend/.env`：
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=spacenose
```

### 步骤 3: 初始化数据库
```bash
cd backend
python init_database.py
```

### 步骤 4: 启动服务器
```bash
python main.py
# 或者双击 start_server.bat
```

看到 `✓ 数据库连接成功: spacenose` 表示配置完成！

---

## 📝 使用示例

### Python 调用示例
```python
import requests

# 获取最近100条数据
response = requests.get('http://localhost:8000/api/data/recent?limit=100')
data = response.json()

print(f"共有 {data['count']} 条记录")
for item in data['data']:
    print(f"电压: {item['voltage']}V, 时间: {item['timestamp']}")
```

### JavaScript 调用示例
```javascript
// 获取统计信息
fetch('http://localhost:8000/api/stats')
  .then(response => response.json())
  .then(data => {
    console.log('总记录数:', data.total_records);
    console.log('最新电压:', data.latest_record.voltage);
  });
```

### 命令行调用示例
```bash
# 获取最近1小时的数据
curl "http://localhost:8000/api/data/hours?hours=1"

# 获取统计信息
curl "http://localhost:8000/api/stats"
```

---

## 📚 文档索引

详细文档请查看：

1. **[backend/QUICK_START_DATABASE.md](backend/QUICK_START_DATABASE.md)**  
   3分钟快速配置指南

2. **[backend/数据库使用说明.md](backend/数据库使用说明.md)**  
   完整的使用手册，包含所有API说明

3. **[backend/数据库集成总结.md](backend/数据库集成总结.md)**  
   技术实现总结和架构说明

4. **[backend/example_usage.py](backend/example_usage.py)**  
   可运行的示例代码，演示所有功能

5. **[README.md](README.md)**  
   项目主文档（已更新）

6. **http://localhost:8000/docs**  
   FastAPI 自动生成的交互式 API 文档

---

## 🗂️ 新增文件清单

```
backend/
├── config.py                 # 配置管理
├── models.py                 # 数据库模型
├── database.py               # CRUD操作
├── init_database.py          # 初始化脚本
├── test_database.py          # 测试脚本
├── example_usage.py          # 使用示例
├── .env                      # 环境变量（需配置）
├── 数据库使用说明.md          # 详细文档
├── QUICK_START_DATABASE.md   # 快速指南
└── 数据库集成总结.md          # 技术总结

根目录/
├── start_server.bat          # 启动脚本
└── MYSQL数据库集成说明.md     # 本文件
```

---

## 🔧 技术细节

### 数据库表结构
```sql
CREATE TABLE sensor_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    counter INT NOT NULL,
    adc INT NOT NULL,
    voltage FLOAT NOT NULL,
    timestamp DATETIME NOT NULL,
    source_ip VARCHAR(50),
    INDEX idx_timestamp (timestamp)
);
```

### 技术栈
- **ORM框架**: SQLAlchemy 2.0
- **MySQL驱动**: PyMySQL
- **连接池**: 内置，自动管理
- **异步支持**: 与 FastAPI 完美集成

### 数据流程
```
UDP数据 → 解析JSON → 保存数据库 + 实时广播
                        ↓              ↓
                     MySQL         WebSocket
                        ↓              ↓
                   持久化存储       前端显示
```

---

## ❓ 常见问题

### Q: 数据库连接失败？
**A:** 运行测试脚本诊断：
```bash
cd backend
python test_database.py
```

### Q: 如何查看已保存的数据？
**A:** 三种方法：
1. 访问 `http://localhost:8000/api/stats`
2. 运行 `python example_usage.py`
3. 使用 MySQL 客户端：`SELECT * FROM sensor_data LIMIT 10;`

### Q: 如何导出数据？
**A:** 使用示例脚本：
```bash
python example_usage.py  # 会生成CSV文件
```

### Q: 数据库占用空间太大？
**A:** 定期清理旧数据：
```bash
curl -X DELETE "http://localhost:8000/api/data/cleanup?days=30"
```

### Q: 不想使用数据库可以吗？
**A:** 可以！数据库保存失败不影响实时功能。如果不配置数据库，系统仍可正常运行，只是没有历史数据功能。

---

## 🎊 升级前后对比

| 功能 | 升级前 | 升级后 |
|------|--------|--------|
| 数据存储 | ❌ 仅内存，重启丢失 | ✅ MySQL持久化 |
| 历史查询 | ❌ 无法查询历史 | ✅ 完整API支持 |
| 数据分析 | ❌ 仅当前值 | ✅ 趋势、统计 |
| 数据导出 | ❌ 不支持 | ✅ CSV导出 |
| 长期运行 | ❌ 内存占用增长 | ✅ 自动清理 |

---

## 📞 获取帮助

- 查看详细文档：`backend/数据库使用说明.md`
- 运行测试脚本：`python backend/test_database.py`
- 查看 API 文档：http://localhost:8000/docs
- 查看示例代码：`backend/example_usage.py`

---

## ✅ 验证配置

运行以下命令验证数据库是否正常工作：

```bash
# 1. 测试数据库连接
cd backend
python test_database.py

# 2. 启动服务器
python main.py

# 3. 在新终端查看统计
curl http://localhost:8000/api/stats

# 4. 运行完整示例
python example_usage.py
```

如果都正常运行，说明数据库集成成功！🎉

---

**祝使用愉快！** 🚀

*星际嗅探者团队*

