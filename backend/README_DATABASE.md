# 数据库模块文档

## 概述

本目录包含星际嗅探者项目的后端服务器代码，包括完整的 MySQL 数据库集成。

## 文件说明

### 核心文件

- **`main.py`** - FastAPI 主服务器
  - UDP 服务器（接收 ESP8266 数据）
  - WebSocket 服务器（实时推送到前端）
  - HTTP/REST API（历史数据查询）
  - 数据库自动保存

- **`config.py`** - 配置管理
  - 读取 `.env` 环境变量
  - 统一的配置接口
  - 数据库连接URL构建

- **`models.py`** - 数据库模型
  - `SensorData` 表定义
  - ORM 映射
  - JSON 序列化方法

- **`database.py`** - 数据库操作
  - 数据库引擎初始化
  - 会话管理
  - CRUD 操作封装
  - 查询方法（按时间、ID等）

### 工具脚本

- **`init_database.py`** - 数据库初始化
  ```bash
  python init_database.py
  ```
  自动创建数据库和表结构

- **`test_database.py`** - 连接测试
  ```bash
  python test_database.py
  ```
  测试数据库连接和配置

- **`example_usage.py`** - 使用示例
  ```bash
  python example_usage.py
  ```
  演示所有 API 的使用方法

### 配置文件

- **`.env`** - 环境变量（需手动配置）
  ```env
  DB_HOST=localhost
  DB_PORT=3306
  DB_USER=root
  DB_PASSWORD=你的密码
  DB_NAME=spacenose
  ```

- **`requirements.txt`** - Python 依赖
  ```bash
  pip install -r requirements.txt
  ```

### 文档文件

- **`数据库使用说明.md`** - 完整使用手册
- **`QUICK_START_DATABASE.md`** - 快速配置指南  
- **`数据库集成总结.md`** - 技术实现总结
- **`README_DATABASE.md`** - 本文件

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置数据库
创建 `.env` 文件（参考上面的配置文件部分）

### 3. 初始化数据库
```bash
python init_database.py
```

### 4. 测试连接
```bash
python test_database.py
```

### 5. 启动服务器
```bash
python main.py
```

## API 接口

启动服务器后，访问以下接口：

### 实时数据
- `GET /api/latest` - 获取最新实时数据

### 历史数据
- `GET /api/data/recent?limit=100` - 最近N条记录
- `GET /api/data/hours?hours=1` - 最近N小时数据
- `GET /api/data/range?start=...&end=...` - 时间范围查询
- `GET /api/data/{id}` - 根据ID查询

### 统计信息
- `GET /api/stats` - 数据库统计信息

### 数据管理
- `DELETE /api/data/cleanup?days=30` - 清理旧数据

### API 文档
- http://localhost:8000/docs - 交互式 API 文档（自动生成）

## 数据库结构

### sensor_data 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键（自增） |
| counter | INT | 数据计数器 |
| adc | INT | ADC原始值 (0-4095) |
| voltage | FLOAT | 电压值 (V) |
| timestamp | DATETIME | 接收时间 |
| source_ip | VARCHAR(50) | 来源IP地址 |

**索引**：
- 主键索引：`id`
- 时间索引：`timestamp`

## 开发指南

### 添加新的查询方法

在 `database.py` 的 `SensorDataCRUD` 类中添加：

```python
@staticmethod
def your_new_query(db: Session, params):
    """查询说明"""
    return db.query(SensorData).filter(...).all()
```

### 添加新的 API 接口

在 `main.py` 中添加：

```python
@app.get("/api/your_endpoint")
async def your_endpoint(db: Session = Depends(get_db)):
    """API说明"""
    data = SensorDataCRUD.your_new_query(db, ...)
    return {"success": True, "data": [item.to_dict() for item in data]}
```

### 修改数据表结构

1. 修改 `models.py` 中的 `SensorData` 类
2. 删除现有表或使用迁移工具
3. 重新运行 `init_database.py`

## 性能优化

### 查询优化
- 使用索引字段查询
- 限制返回记录数（`limit`）
- 使用时间范围而非全表查询

### 数据维护
- 定期清理旧数据
- 定期备份数据库
- 监控数据库大小

### 连接池配置
当前配置（在 `database.py` 中）：
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,    # 连接检查
    pool_recycle=3600,     # 每小时回收
    echo=False             # 不打印SQL
)
```

## 故障排查

### 数据库连接失败
1. 检查 MySQL 服务是否启动
2. 验证 `.env` 配置是否正确
3. 运行 `python test_database.py` 查看详细错误

### 数据未保存
1. 查看服务器日志中的错误信息
2. 确认数据库用户有写入权限
3. 检查表是否存在

### 查询缓慢
1. 确认使用了索引字段
2. 检查数据量，考虑分页
3. 定期执行 `OPTIMIZE TABLE sensor_data`

## 安全建议

1. **不要提交 `.env` 文件到版本控制**
2. **使用强密码**
3. **限制数据库用户权限**
4. **定期备份数据**
5. **使用 HTTPS（生产环境）**

## 相关资源

- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [MySQL 文档](https://dev.mysql.com/doc/)
- [项目主 README](../README.md)

## 许可证

与主项目相同

---

*星际嗅探者团队*

