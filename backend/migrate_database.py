"""
数据库迁移脚本 - 为传感器数据表添加MQ-3酒精传感器字段
运行此脚本以更新现有数据库结构
"""
from sqlalchemy import text
from database import engine, init_db
from config import settings

def migrate_database():
    """迁移数据库，添加新字段"""
    print("========================================")
    print("  数据库迁移：添加MQ-3传感器字段")
    print("========================================\n")

    try:
        with engine.connect() as connection:
            # 检查字段是否已存在
            result = connection.execute(text(
                f"SELECT COUNT(*) FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA='{settings.DB_NAME}' "
                f"AND TABLE_NAME='sensor_data' "
                f"AND COLUMN_NAME='mq3_adc'"
            ))
            exists = result.scalar() > 0

            if exists:
                print("✓ MQ-3字段已存在，无需迁移")
                return True

            print("正在添加新字段...")

            # 添加新字段
            connection.execute(text(
                "ALTER TABLE sensor_data ADD COLUMN mq3_adc INT NULL COMMENT 'MQ-3传感器ADC原始值'"
            ))
            connection.execute(text(
                "ALTER TABLE sensor_data ADD COLUMN mq3_voltage FLOAT NULL COMMENT 'MQ-3传感器电压值'"
            ))
            connection.execute(text(
                "ALTER TABLE sensor_data ADD COLUMN alcohol_ppm FLOAT NULL COMMENT '酒精浓度(ppm)'"
            ))
            connection.execute(text(
                "ALTER TABLE sensor_data ADD COLUMN sensor_status INT NULL COMMENT '传感器状态(0=正常,1=预热中)'"
            ))

            connection.commit()
            print("✓ 字段添加成功！")
            print("\n新增字段：")
            print("  - mq3_adc (INT): MQ-3传感器ADC原始值")
            print("  - mq3_voltage (FLOAT): MQ-3传感器电压值")
            print("  - alcohol_ppm (FLOAT): 酒精浓度(ppm)")
            print("  - sensor_status (INT): 传感器状态")
            print("\n========================================")
            return True

    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        print("\n如果数据库不存在，将自动创建新表...")
        # 尝试直接创建表
        if init_db():
            print("✓ 数据库表创建成功")
            return True
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✓ 数据库迁移完成！")
    else:
        print("\n✗ 数据库迁移失败，请检查配置和权限")
