#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试个股诊断模块的API接口
"""

import os
import sys
import django
import requests
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://192.168.2.92:5173"
    
    print("🧪 测试个股诊断模块API接口")
    print("=" * 50)
    
    # 测试1: 指数数据API
    print("\n1. 测试指数数据API...")
    try:
        response = requests.get(f"{base_url}/api/stock_analysis/index/")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   错误响应: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")
    
    # 测试2: 股票搜索API
    print("\n2. 测试股票搜索API...")
    try:
        response = requests.get(f"{base_url}/api/stock_analysis/search/?q=000001")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   错误响应: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")
    
    # 测试3: 股票信息API
    print("\n3. 测试股票信息API...")
    try:
        response = requests.get(f"{base_url}/api/stock_analysis/stock/000001/")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   错误响应: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")
    
    # 测试4: 图表数据API
    print("\n4. 测试图表数据API...")
    try:
        response = requests.get(f"{base_url}/api/stock_analysis/chart/000001/")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   错误响应: {response.text}")
    except Exception as e:
        print(f"   请求失败: {e}")

def test_database_connection():
    """测试数据库连接"""
    print("\n🔍 测试数据库连接...")
    
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
            print(f"      指数代码: {index_data['ts_code'].unique()}")
        else:
            print("   ⚠️  指数数据为空")
            
    except Exception as e:
        print(f"   ❌ 数据库测试失败: {e}")

def test_url_patterns():
    """测试URL模式"""
    print("\n🔗 测试URL模式...")
    
    try:
        from django.urls import reverse
        from stock_analysis.urls import urlpatterns
        
        print(f"   ✅ 找到 {len(urlpatterns)} 个URL模式:")
        for pattern in urlpatterns:
            print(f"      - {pattern.pattern}")
            
    except Exception as e:
        print(f"   ❌ URL模式测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试个股诊断模块...")
    
    # 测试URL模式
    test_url_patterns()
    
    # 测试数据库连接
    test_database_connection()
    
    # 测试API端点（需要Django服务运行）
    print("\n⚠️  注意: 以下API测试需要Django服务正在运行")
    print("   请确保已运行: python manage.py runserver")
    
    test_api_endpoints()
    
    print("\n🎯 测试完成！")
