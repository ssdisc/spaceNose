"""
配置文件 - 管理数据库和服务器配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings:
    """应用配置类"""
    
    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "spacenose")
    
    # 构建数据库连接URL
    DATABASE_URL: str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    
    # 服务器配置
    UDP_HOST: str = os.getenv("UDP_HOST", "0.0.0.0")
    UDP_PORT: int = int(os.getenv("UDP_PORT", "8888"))
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

# 创建配置实例
settings = Settings()

