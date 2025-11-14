"""
数据库操作 - 处理数据库连接和CRUD操作
"""
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from models import Base, SensorData
from config import settings
from typing import List, Optional
from datetime import datetime, timedelta

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 自动检查连接是否有效
    pool_recycle=3600,   # 每小时回收连接
    echo=False           # 不打印SQL语句，生产环境建议设为False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ 数据库表创建成功")
        return True
    except SQLAlchemyError as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

def get_db():
    """获取数据库会话的依赖注入函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SensorDataCRUD:
    """传感器数据的CRUD操作类"""
    
    @staticmethod
    def create(db: Session, counter: int, adc: int, voltage: float, source_ip: str = None) -> Optional[SensorData]:
        """创建新的传感器数据记录"""
        try:
            sensor_data = SensorData(
                counter=counter,
                adc=adc,
                voltage=voltage,
                timestamp=datetime.now(),
                source_ip=source_ip
            )
            db.add(sensor_data)
            db.commit()
            db.refresh(sensor_data)
            return sensor_data
        except SQLAlchemyError as e:
            db.rollback()
            print(f"✗ 数据插入失败: {e}")
            return None
    
    @staticmethod
    def get_latest(db: Session, limit: int = 100) -> List[SensorData]:
        """获取最新的N条数据"""
        try:
            return db.query(SensorData).order_by(desc(SensorData.id)).limit(limit).all()
        except SQLAlchemyError as e:
            print(f"✗ 查询失败: {e}")
            return []
    
    @staticmethod
    def get_by_id(db: Session, data_id: int) -> Optional[SensorData]:
        """根据ID获取数据"""
        try:
            return db.query(SensorData).filter(SensorData.id == data_id).first()
        except SQLAlchemyError as e:
            print(f"✗ 查询失败: {e}")
            return None
    
    @staticmethod
    def get_by_time_range(db: Session, start_time: datetime, end_time: datetime) -> List[SensorData]:
        """根据时间范围获取数据"""
        try:
            return db.query(SensorData).filter(
                SensorData.timestamp >= start_time,
                SensorData.timestamp <= end_time
            ).order_by(SensorData.timestamp).all()
        except SQLAlchemyError as e:
            print(f"✗ 查询失败: {e}")
            return []
    
    @staticmethod
    def get_recent_hours(db: Session, hours: int = 1) -> List[SensorData]:
        """获取最近N小时的数据"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            return db.query(SensorData).filter(
                SensorData.timestamp >= start_time
            ).order_by(SensorData.timestamp).all()
        except SQLAlchemyError as e:
            print(f"✗ 查询失败: {e}")
            return []
    
    @staticmethod
    def get_count(db: Session) -> int:
        """获取总记录数"""
        try:
            return db.query(SensorData).count()
        except SQLAlchemyError as e:
            print(f"✗ 查询失败: {e}")
            return 0
    
    @staticmethod
    def delete_old_data(db: Session, days: int = 30) -> int:
        """删除N天前的旧数据"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            deleted_count = db.query(SensorData).filter(
                SensorData.timestamp < cutoff_time
            ).delete()
            db.commit()
            return deleted_count
        except SQLAlchemyError as e:
            db.rollback()
            print(f"✗ 删除失败: {e}")
            return 0

