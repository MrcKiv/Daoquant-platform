#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的个股诊断API
"""

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_main.backend.settings')
django.setup()

def test_views():
    """测试视图函数"""
    print("🧪 测试视图函数...")
    
    try:
        from stock_analysis.views import (
            get_stock_info_api,
            get_stock_chart_data_api,
            search_stocks_api,
            get_index_data_api
        )
        
        # 创建模拟请求对象
        from django.test import RequestFactory
        from django.http import HttpRequest
        
        factory = RequestFactory()
        
        # 测试1: 股票信息API
        print("\n1. 测试股票信息API...")
        try:
            request = factory.get('/api/stock_analysis/stock/000001/')
            response = get_stock_info_api(request, '000001')
            print(f"   ✅ 股票信息API正常，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 股票信息API失败: {e}")
        
        # 测试2: 图表数据API
        print("\n2. 测试图表数据API...")
        try:
            request = factory.get('/api/stock_analysis/chart/000001/')
            response = get_stock_chart_data_api(request, '000001')
            print(f"   ✅ 图表数据API正常，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 图表数据API失败: {e}")
        
        # 测试3: 搜索API
        print("\n3. 测试搜索API...")
        try:
            request = factory.get('/api/stock_analysis/search/?q=000001')
            response = search_stocks_api(request)
            print(f"   ✅ 搜索API正常，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 搜索API失败: {e}")
        
        # 测试4: 指数数据API
        print("\n4. 测试指数数据API...")
        try:
            request = factory.get('/api/stock_analysis/index/')
            response = get_index_data_api(request)
            print(f"   ✅ 指数数据API正常，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 指数数据API失败: {e}")
        
    except Exception as e:
        print(f"❌ 视图测试失败: {e}")

def test_urls():
    """测试URL配置"""
    print("\n🔗 测试URL配置...")
    
    try:
        from django.urls import reverse, resolve
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # 测试URL解析
        test_urls = [
            '/api/stock_analysis/index/',
            '/api/stock_analysis/search/',
            '/api/stock_analysis/stock/000001/',
            '/api/stock_analysis/chart/000001/'
        ]
        
        for url in test_urls:
            try:
                match = resolve(url)
                print(f"   ✅ {url} -> {match.func.__name__}")
            except Exception as e:
                print(f"   ❌ {url} -> {e}")
                
    except Exception as e:
        print(f"❌ URL测试失败: {e}")

def test_database():
    """测试数据库连接"""
    print("\n🗄️  测试数据库连接...")
    
    try:
        from stock_analysis.views import get_db_connection, get_index_data
        
        # 测试数据库连接
        conn = get_db_connection()
        print("   ✅ 数据库连接成功")
        conn.close()
        
        # 测试获取指数数据
        index_data = get_index_data()
        if not index_data.empty:
            print(f"   ✅ 获取指数数据成功，共 {len(index_data)} 条记录")
        else:
            print("   ⚠️  指数数据为空")
            
    except Exception as e:
        print(f"   ❌ 数据库测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试修复后的API...")
    
    test_views()
    test_urls()
    test_database()
    
    print("\n🎯 测试完成！")

