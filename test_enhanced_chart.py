#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版图表数据结构
"""

import sys
import os
import django

# 设置Django环境
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_main'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# 初始化Django
django.setup()

from stock_analysis.views import get_stock_chart_data_api
from django.test import RequestFactory
import json

def test_enhanced_chart_data():
    """测试增强版图表数据"""
    print("🚀 开始测试增强版图表数据...")
    
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
            
            # 检查所有必需的数据字段
            required_fields = {
                'dates': '日期数组',
                'prices': {
                    'open': '开盘价',
                    'high': '最高价', 
                    'low': '最低价',
                    'close': '收盘价'
                },
                'volume': '成交量',
                'indicators': {
                    'ma5': 'MA5均线',
                    'ma10': 'MA10均线',
                    'ma20': 'MA20均线',
                    'rsi': 'RSI指标',
                    'macd': 'MACD指标',
                    'macd_signal': 'MACD信号线',
                    'macd_histogram': 'MACD柱状图',
                    'kdj_k': 'KDJ-K线',
                    'kdj_d': 'KDJ-D线',
                    'kdj_j': 'KDJ-J线',
                    'boll_upper': '布林带上轨',
                    'boll_middle': '布林带中轨',
                    'boll_lower': '布林带下轨'
                }
            }
            
            print("\n🔍 检查数据完整性...")
            
            # 检查日期
            dates = response_data.get('dates', [])
            if dates:
                print(f"✅ 日期数据: {len(dates)} 个")
                print(f"  前3个: {dates[:3]}")
                print(f"  后3个: {dates[-3:]}")
            else:
                print("❌ 缺少日期数据")
            
            # 检查价格数据
            prices = response_data.get('prices', {})
            if prices:
                print(f"✅ 价格数据:")
                for key, desc in required_fields['prices'].items():
                    data = prices.get(key, [])
                    print(f"  {desc}: {len(data)} 个")
            else:
                print("❌ 缺少价格数据")
            
            # 检查成交量
            volume = response_data.get('volume', [])
            if volume:
                print(f"✅ 成交量数据: {len(volume)} 个")
            else:
                print("❌ 缺少成交量数据")
            
            # 检查技术指标
            indicators = response_data.get('indicators', {})
            if indicators:
                print(f"✅ 技术指标数据:")
                for key, desc in required_fields['indicators'].items():
                    data = indicators.get(key, [])
                    if data:
                        print(f"  {desc}: {len(data)} 个")
                        # 检查是否有有效数据（非None）
                        valid_count = sum(1 for x in data if x is not None)
                        print(f"    有效数据: {valid_count} 个")
                    else:
                        print(f"  {desc}: 缺少数据")
            else:
                print("❌ 缺少技术指标数据")
            
            # 测试JSON序列化
            try:
                json_str = json.dumps(response_data)
                print(f"\n✅ JSON序列化成功，长度: {len(json_str)} 字符")
                
                # 检查数据大小
                print(f"\n📊 数据统计:")
                print(f"  总数据点: {len(dates)}")
                print(f"  价格字段: {len(prices)} 个")
                print(f"  技术指标: {len(indicators)} 个")
                
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
    test_enhanced_chart_data()
