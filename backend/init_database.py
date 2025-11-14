"""
数据库初始化脚本
用于创建数据库和表结构
"""
import pymysql
from config import settings
from database import init_db

def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 连接MySQL服务器（不指定数据库）
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ 数据库 '{settings.DB_NAME}' 创建成功或已存在")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"✗ 数据库创建失败: {e}")
        return False

def main():
    """主函数：完整的数据库初始化流程"""
    print("=" * 50)
    print("  星际嗅探者 - 数据库初始化")
    print("=" * 50)
    print(f"数据库主机: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"数据库名称: {settings.DB_NAME}")
    print(f"数据库用户: {settings.DB_USER}")
    print("=" * 50)
    
    # 步骤1: 创建数据库
    print("\n[1/2] 创建数据库...")
    if not create_database():
        print("\n❌ 数据库初始化失败！")
        return False
    
    # 步骤2: 创建表结构
    print("\n[2/2] 创建数据表...")
    if init_db():
        print("\n✅ 数据库初始化完成！")
        print(f"\n数据库 '{settings.DB_NAME}' 已准备就绪，可以开始使用了。")
        return True
    else:
        print("\n❌ 表结构创建失败！")
        return False

if __name__ == "__main__":
    main()

