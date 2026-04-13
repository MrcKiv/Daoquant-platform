#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的架构设计：分离基本信息和行情数据
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
    """测试搜索函数（只返回基本信息）"""
    print("🧪 测试搜索函数（基本信息）...")
    
    try:
        from stock_analysis.views import search_stocks
        
        # 测试股票代码搜索
        print("\n1. 测试股票代码搜索 (000001)...")
        results = search_stocks('000001', limit=3)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     行业: {stock.get('industry', 'N/A')}")
                print(f"     地区: {stock.get('area', 'N/A')}")
                print(f"     市场: {stock.get('market', 'N/A')}")
        else:
            print("   ❌ 未找到结果")
        
        # 测试股票名称搜索
        print("\n2. 测试股票名称搜索 (平安)...")
        results = search_stocks('平安', limit=3)
        if results:
            print(f"   找到 {len(results)} 个结果:")
            for stock in results:
                print(f"   - {stock['st_code']}: {stock['name']}")
                print(f"     行业: {stock.get('industry', 'N/A')}")
        else:
            print("   ❌ 未找到结果")
        
    except Exception as e:
        print(f"❌ 搜索测试失败: {e}")

def test_latest_quote():
    """测试获取最新行情数据"""
    print("\n📊 测试获取最新行情数据...")
    
    try:
        from stock_analysis.views import get_stock_latest_quote
        
        # 测试获取000001的最新行情
        print("\n1. 测试获取000001的最新行情...")
        quote = get_stock_latest_quote('000001')
        if quote:
            print(f"   股票代码: {quote.get('st_code')}")
            print(f"   最新价格: {quote.get('latest_price')}")
            print(f"   涨跌幅: {quote.get('latest_change')}%")
            print(f"   成交量: {quote.get('latest_volume')}")
            print(f"   交易日期: {quote.get('latest_date')}")
            print(f"   MACD: {quote.get('latest_macd')}")
            print(f"   RSI: {quote.get('latest_rsi')}")
            print(f"   KDJ_K: {quote.get('latest_kdj_k')}")
            print(f"   KDJ_D: {quote.get('latest_kdj_d')}")
            print(f"   BOLL: {quote.get('latest_boll')}")
            print(f"   CCI: {quote.get('latest_cci')}")
        else:
            print("   ❌ 未找到行情数据")
        
    except Exception as e:
        print(f"❌ 行情数据测试失败: {e}")

def test_stock_info_api():
    """测试股票信息API（包含基本信息和行情数据）"""
    print("\n🔗 测试股票信息API...")
    
    try:
        from stock_analysis.views import get_stock_info_api
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # 测试获取000001的完整信息
        print("\n1. 测试获取000001的完整信息...")
        request = factory.get('/api/stock_analysis/stock/000001/')
        response = get_stock_info_api(request, '000001')
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ API调用成功")
            
            if data.get('basic_info'):
                basic = data['basic_info']
                print(f"   基本信息: {basic['st_code']} - {basic['name']}")
                print(f"   行业: {basic.get('industry')}")
                print(f"   地区: {basic.get('area')}")
            
            if data.get('latest_quote'):
                quote = data['latest_quote']
                print(f"   最新行情: 价格{quote.get('latest_price')}, 涨跌{quote.get('latest_change')}%")
            
            if data.get('daily_data'):
                print(f"   历史数据: {len(data['daily_data'])} 条记录")
            
            if data.get('diagnosis'):
                diagnosis = data['diagnosis']
                print(f"   诊断结果: 综合评分{diagnosis.get('overall_score')}, 建议{diagnosis.get('recommendation')}")
        else:
            print(f"   ❌ API调用失败: {response.status_code}")
            print(f"   错误信息: {response.content}")
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def test_database_tables():
    """测试数据库表结构"""
    print("\n🗄️  测试数据库表结构...")
    
    try:
        from stock_analysis.views import get_db_connection
        import pandas as pd
        
        conn = get_db_connection()
        
        # 测试股票基本信息表
        print("\n1. 股票基本信息remove表:")
        df = pd.read_sql("SELECT * FROM `股票基本信息remove` LIMIT 3", conn)
        print(f"   列名: {list(df.columns)}")
        print(f"   数据形状: {df.shape}")
        
        # 测试partition_table表
        print("\n2. partition_table表:")
        df = pd.read_sql("SELECT * FROM partition_table LIMIT 3", conn)
        print(f"   列名: {list(df.columns)}")
        print(f"   数据形状: {df.shape}")
        
        # 测试大盘指数表
        print("\n3. 大盘指数表:")
        df = pd.read_sql("SELECT * FROM `大盘指数` LIMIT 3", conn)
        print(f"   列名: {list(df.columns)}")
        print(f"   数据形状: {df.shape}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库表结构测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试新的架构设计...")
    
    test_database_tables()
    test_search_function()
    test_latest_quote()
    test_stock_info_api()
    
    print("\n🎯 测试完成！")
    print("\n📋 架构总结:")
    print("1. 搜索功能: 从股票基本信息remove表获取基本信息")
    print("2. 行情数据: 从partition_table表获取最新行情和技术指标")
    print("3. 图表数据: 从partition_table表获取历史数据用于绘制K线图")
    print("4. 指数数据: 从大盘指数表获取主要指数信息")

