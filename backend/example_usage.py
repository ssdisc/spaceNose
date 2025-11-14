"""
数据库使用示例
演示如何使用数据库API和CRUD操作
"""
import requests
import json
from datetime import datetime, timedelta

# 服务器地址
BASE_URL = "http://localhost:8000"

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def example_get_latest():
    """示例1: 获取实时最新数据"""
    print_section("示例1: 获取实时最新数据")
    
    response = requests.get(f"{BASE_URL}/api/latest")
    data = response.json()
    
    print(f"计数: {data.get('counter')}")
    print(f"ADC值: {data.get('adc')}")
    print(f"电压: {data.get('voltage')} V")
    print(f"时间: {data.get('timestamp')}")

def example_get_recent():
    """示例2: 获取最近的数据库记录"""
    print_section("示例2: 获取最近50条数据库记录")
    
    response = requests.get(f"{BASE_URL}/api/data/recent?limit=50")
    data = response.json()
    
    if data['success']:
        print(f"✓ 成功获取 {data['count']} 条记录")
        if data['data']:
            # 显示前3条
            print("\n前3条记录:")
            for item in data['data'][:3]:
                print(f"  ID: {item['id']}, 电压: {item['voltage']}V, 时间: {item['timestamp']}")
    else:
        print("✗ 获取失败")

def example_get_hours():
    """示例3: 获取最近N小时的数据"""
    print_section("示例3: 获取最近1小时的数据")
    
    response = requests.get(f"{BASE_URL}/api/data/hours?hours=1")
    data = response.json()
    
    if data['success']:
        print(f"✓ 最近 {data['hours']} 小时内有 {data['count']} 条记录")
        
        # 计算平均电压
        if data['data']:
            voltages = [item['voltage'] for item in data['data']]
            avg_voltage = sum(voltages) / len(voltages)
            print(f"  平均电压: {avg_voltage:.3f} V")
            print(f"  最大电压: {max(voltages):.3f} V")
            print(f"  最小电压: {min(voltages):.3f} V")
    else:
        print("✗ 获取失败")

def example_get_by_time_range():
    """示例4: 根据时间范围查询"""
    print_section("示例4: 根据时间范围查询数据")
    
    # 查询最近10分钟的数据
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    
    params = {
        'start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end': end_time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    response = requests.get(f"{BASE_URL}/api/data/range", params=params)
    data = response.json()
    
    if data['success']:
        print(f"✓ 时间范围: {params['start']} 至 {params['end']}")
        print(f"  找到 {data['count']} 条记录")
    else:
        print(f"✗ 查询失败: {data.get('error')}")

def example_get_by_id():
    """示例5: 根据ID获取单条记录"""
    print_section("示例5: 根据ID获取单条记录")
    
    # 先获取最新记录的ID
    response = requests.get(f"{BASE_URL}/api/data/recent?limit=1")
    recent_data = response.json()
    
    if recent_data['success'] and recent_data['data']:
        data_id = recent_data['data'][0]['id']
        
        # 根据ID查询
        response = requests.get(f"{BASE_URL}/api/data/{data_id}")
        data = response.json()
        
        if data['success']:
            item = data['data']
            print(f"✓ 记录详情:")
            print(f"  ID: {item['id']}")
            print(f"  计数器: {item['counter']}")
            print(f"  ADC值: {item['adc']}")
            print(f"  电压: {item['voltage']} V")
            print(f"  时间: {item['timestamp']}")
            print(f"  来源IP: {item['source_ip']}")
        else:
            print("✗ 获取失败")
    else:
        print("⚠ 数据库中暂无数据")

def example_get_stats():
    """示例6: 获取统计信息"""
    print_section("示例6: 获取数据统计信息")
    
    response = requests.get(f"{BASE_URL}/api/stats")
    data = response.json()
    
    if data['success']:
        print(f"✓ 数据库: {data['database']}")
        print(f"  总记录数: {data['total_records']}")
        
        if data['latest_record']:
            latest = data['latest_record']
            print(f"  最新记录:")
            print(f"    电压: {latest['voltage']} V")
            print(f"    时间: {latest['timestamp']}")
    else:
        print("✗ 获取失败")

def example_export_to_csv():
    """示例7: 导出数据为CSV"""
    print_section("示例7: 导出数据为CSV文件")
    
    response = requests.get(f"{BASE_URL}/api/data/recent?limit=100")
    data = response.json()
    
    if data['success'] and data['data']:
        filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入表头
            f.write("ID,计数器,ADC值,电压(V),时间戳,来源IP\n")
            
            # 写入数据
            for item in data['data']:
                f.write(f"{item['id']},{item['counter']},{item['adc']},{item['voltage']},{item['timestamp']},{item['source_ip']}\n")
        
        print(f"✓ 成功导出 {len(data['data'])} 条记录到 {filename}")
    else:
        print("⚠ 没有数据可导出")

def example_analyze_data():
    """示例8: 数据分析"""
    print_section("示例8: 数据分析 - 电压趋势")
    
    response = requests.get(f"{BASE_URL}/api/data/hours?hours=1")
    data = response.json()
    
    if data['success'] and data['data']:
        records = data['data']
        print(f"✓ 分析最近1小时的 {len(records)} 条数据\n")
        
        # 计算统计信息
        voltages = [item['voltage'] for item in records]
        avg = sum(voltages) / len(voltages)
        max_v = max(voltages)
        min_v = min(voltages)
        
        print(f"电压统计:")
        print(f"  平均值: {avg:.3f} V")
        print(f"  最大值: {max_v:.3f} V")
        print(f"  最小值: {min_v:.3f} V")
        print(f"  波动范围: {max_v - min_v:.3f} V")
        
        # 简单的趋势分析
        if len(records) > 1:
            first_voltage = records[-1]['voltage']  # 最早的记录
            last_voltage = records[0]['voltage']    # 最新的记录
            trend = last_voltage - first_voltage
            
            print(f"\n趋势分析:")
            if trend > 0.1:
                print(f"  ↑ 电压上升 {trend:.3f} V")
            elif trend < -0.1:
                print(f"  ↓ 电压下降 {abs(trend):.3f} V")
            else:
                print(f"  → 电压稳定 (变化 {abs(trend):.3f} V)")
    else:
        print("⚠ 数据不足，无法分析")

def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 60)
    print("  星际嗅探者 - 数据库API使用示例")
    print("=" * 60)
    print("\n⚠ 注意: 请确保后端服务器已启动 (python main.py)")
    print(f"服务器地址: {BASE_URL}")
    
    try:
        # 测试连接
        response = requests.get(f"{BASE_URL}/api/stats", timeout=2)
        if response.status_code == 200:
            print("✓ 服务器连接正常\n")
        else:
            print("✗ 服务器响应异常\n")
            return
    except requests.exceptions.RequestException:
        print("✗ 无法连接到服务器，请先启动后端服务\n")
        return
    
    # 运行所有示例
    try:
        example_get_stats()
        example_get_latest()
        example_get_recent()
        example_get_hours()
        example_get_by_time_range()
        example_get_by_id()
        example_analyze_data()
        example_export_to_csv()
        
        print("\n" + "=" * 60)
        print("  ✅ 所有示例运行完成")
        print("=" * 60)
        print("\n更多API信息请访问: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")

if __name__ == "__main__":
    main()

