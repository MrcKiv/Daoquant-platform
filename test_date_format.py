#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试后端返回的日期格式
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_main'))

from stock_analysis.views import get_stock_chart_data_api
from django.test import RequestFactory
from django.http import JsonResponse
import json

def test_date_format():
    """测试日期格式"""
    print("🚀 开始测试日期格式...")
    
    # 模拟Django请求
    factory = RequestFactory()
    request = factory.get('/chart/000001.SZ/')
    
    try:
        # 调用图表数据API
        response = get_stock_chart_data_api(request, '000001.SZ')
        
        if response.status_code == 200:
            # 获取响应数据
            response_data = json.loads(response.content)
            
            print("\n✅ API调用成功")
            print(f"数据长度: {len(response_data.get('dates', []))}")
            
            # 检查日期格式
            dates = response_data.get('dates', [])
            if dates:
                print(f"\n📅 前5个日期格式:")
                for i, date in enumerate(dates[:5]):
                    print(f"  第{i+1}个: {date} (类型: {type(date).__name__})")
                
                # 检查是否有Timestamp对象
                timestamp_count = sum(1 for date in dates if 'Timestamp' in str(type(date)))
                print(f"\n🔍 Timestamp对象数量: {timestamp_count}")
                
                if timestamp_count > 0:
                    print("⚠️  发现Timestamp对象，需要在前端转换")
                else:
                    print("✅ 所有日期都是字符串格式")
            
            # 检查其他数据
            prices = response_data.get('prices', {})
            if prices:
                print(f"\n💰 价格数据:")
                print(f"  开盘价: {len(prices.get('open', []))} 个")
                print(f"  收盘价: {len(prices.get('close', []))} 个")
                print(f"  最高价: {len(prices.get('high', []))} 个")
                print(f"  最低价: {len(prices.get('low', []))} 个")
            
            indicators = response_data.get('indicators', {})
            if indicators:
                print(f"\n📊 技术指标:")
                print(f"  MA5: {len(indicators.get('ma5', []))} 个")
                print(f"  MA10: {len(indicators.get('ma10', []))} 个")
                print(f"  MA20: {len(indicators.get('ma20', []))} 个")
                print(f"  RSI: {len(indicators.get('rsi', []))} 个")
                print(f"  MACD: {len(indicators.get('macd', []))} 个")
            
            # 测试JSON序列化
            try:
                json_str = json.dumps(response_data)
                print(f"\n✅ JSON序列化成功，长度: {len(json_str)} 字符")
            except Exception as e:
                print(f"\n❌ JSON序列化失败: {e}")
                
        else:
            print(f"\n❌ API调用失败，状态码: {response.status_code}")
            if hasattr(response, 'content'):
                print(f"错误信息: {response.content.decode()}")
                
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_date_format()
