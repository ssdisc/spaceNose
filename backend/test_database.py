"""
数据库连接测试脚本
用于验证数据库配置是否正确
"""
import sys
import pymysql
from config import settings

def test_mysql_connection():
    """测试MySQL服务器连接"""
    print("=" * 60)
    print("  MySQL 数据库连接测试")
    print("=" * 60)
    print(f"主机: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"用户: {settings.DB_USER}")
    print(f"数据库: {settings.DB_NAME}")
    print("=" * 60)
    print()
    
    try:
        # 测试连接到 MySQL 服务器
        print("[1/3] 测试 MySQL 服务器连接...")
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4'
        )
        print("✓ MySQL 服务器连接成功")
        connection.close()
        
        # 测试连接到指定数据库
        print("\n[2/3] 测试数据库连接...")
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            charset='utf8mb4'
        )
        print(f"✓ 数据库 '{settings.DB_NAME}' 连接成功")
        
        # 测试查询
        print("\n[3/3] 测试数据表...")
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print(f"✓ 找到 {len(tables)} 个数据表:")
            for table in tables:
                print(f"  - {table[0]}")
                
                # 如果是 sensor_data 表，显示记录数
                if table[0] == 'sensor_data':
                    cursor.execute("SELECT COUNT(*) FROM sensor_data")
                    count = cursor.fetchone()[0]
                    print(f"    当前记录数: {count}")
        else:
            print("⚠ 数据库中没有表，请运行 init_database.py 初始化")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！数据库配置正确")
        print("=" * 60)
        print("\n下一步:")
        print("1. 运行 python main.py 启动服务器")
        print("2. 或直接运行根目录下的 start_server.bat")
        return True
        
    except pymysql.err.OperationalError as e:
        error_code = e.args[0]
        print(f"\n❌ 连接失败 (错误代码: {error_code})")
        print(f"错误信息: {e.args[1]}")
        print("\n可能的原因:")
        
        if error_code == 2003:
            print("1. MySQL 服务未启动")
            print("   解决: 启动 MySQL 服务")
            print("   Windows: 服务管理器中启动 MySQL 服务")
            print("   Linux: sudo systemctl start mysql")
        elif error_code == 1045:
            print("1. 用户名或密码错误")
            print("   解决: 检查 .env 文件中的 DB_USER 和 DB_PASSWORD")
        elif error_code == 1049:
            print(f"1. 数据库 '{settings.DB_NAME}' 不存在")
            print("   解决: 运行 python init_database.py 创建数据库")
        else:
            print("1. 检查防火墙设置")
            print("2. 检查 MySQL 是否允许远程连接")
            print(f"3. 检查端口 {settings.DB_PORT} 是否被占用")
        
        print(f"\n当前配置 (backend/.env):")
        print(f"  DB_HOST={settings.DB_HOST}")
        print(f"  DB_PORT={settings.DB_PORT}")
        print(f"  DB_USER={settings.DB_USER}")
        print(f"  DB_NAME={settings.DB_NAME}")
        
        return False
        
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False

def main():
    """主函数"""
    success = test_mysql_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

