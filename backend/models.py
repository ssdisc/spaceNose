"""
数据库模型 - 定义传感器数据表结构
"""
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class SensorData(Base):
    """传感器数据模型"""
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    counter = Column(Integer, nullable=False, comment="数据计数器")
    adc = Column(Integer, nullable=False, comment="ADC原始值")
    voltage = Column(Float, nullable=False, comment="转换后的电压值")
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True, comment="数据接收时间")
    source_ip = Column(String(50), nullable=True, comment="数据来源IP地址")
    
    def __repr__(self):
        return f"<SensorData(id={self.id}, counter={self.counter}, voltage={self.voltage}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "counter": self.counter,
            "adc": self.adc,
            "voltage": self.voltage,
            "timestamp": self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            "source_ip": self.source_ip
        }

