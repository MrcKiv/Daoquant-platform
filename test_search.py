#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的股票搜索功能
"""

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_main.backend.settings')
django.setup()

def test_search_function():
    """测试搜索函数"""
    print("🧪 测试新的股票搜索功能...")
    
    try:
        from stock_analysis.views import search_stocks
        
        # 测试1: 股票代码搜索
        print("\n1. 测试股票代码搜索 (000001)...")
        results = search_stocks('000001', limit=5)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     价格: {stock.get('latest_price', 'N/A')}")
                print(f"     涨跌: {stock.get('latest_change', 'N/A')}%")
                print(f"     行业: {stock.get('industry', 'N/A')}")
        else:
            print("   ❌ 未找到结果")
        
        # 测试2: 股票名称搜索
        print("\n2. 测试股票名称搜索 (平安)...")
        results = search_stocks('平安', limit=5)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     价格: {stock.get('latest_price', 'N/A')}")
                print(f"     涨跌: {stock.get('latest_change', 'N/A')}%")
        else:
            print("   ❌ 未找到结果")
        
        # 测试3: 行业搜索
        print("\n3. 测试行业搜索 (银行)...")
        results = search_stocks('银行', limit=5)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     行业: {stock.get('industry', 'N/A')}")
        else:
            print("   ❌ 未找到结果")
        
        # 测试4: 地区搜索
        print("\n4. 测试地区搜索 (深圳)...")
        results = search_stocks('深圳', limit=5)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     地区: {stock.get('area', 'N/A')}")
        else:
            print("   ❌ 未找到结果")
        
    except Exception as e:
        print(f"❌ 搜索测试失败: {e}")

def test_database_connection():
    """测试数据库连接"""
    print("\n🗄️  测试数据库连接...")
    
    try:
        from stock_analysis.views import get_db_connection
        
        conn = get_db_connection()
        print("   ✅ 数据库连接成功")
        
        # 测试查询partition_table
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM partition_table")
            count = cursor.fetchone()[0]
            print(f"   ✅ partition_table 表有 {count} 条记录")
            
            cursor.execute("SELECT COUNT(*) FROM `股票基本信息remove`")
            count = cursor.fetchone()[0]
            print(f"   ✅ 股票基本信息remove 表有 {count} 条记录")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ 数据库测试失败: {e}")

def test_sample_data():
    """测试样本数据"""
    print("\n📊 测试样本数据...")
    
    try:
        from stock_analysis.views import get_db_connection
        import pandas as pd
        
        conn = get_db_connection()
        
        # 查看partition_table的样本数据
        print("   partition_table 样本数据:")
        df = pd.read_sql("SELECT * FROM partition_table LIMIT 3", conn)
        print(f"   列名: {list(df.columns)}")
        print(f"   数据形状: {df.shape}")
        
        # 查看股票基本信息表的样本数据
        print("\n   股票基本信息remove 样本数据:")
        df = pd.read_sql("SELECT * FROM `股票基本信息remove` LIMIT 3", conn)
        print(f"   列名: {list(df.columns)}")
        print(f"   数据形状: {df.shape}")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ 样本数据测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试新的搜索功能...")
    
    test_database_connection()
    test_sample_data()
    test_search_function()
    
    print("\n🎯 测试完成！")

