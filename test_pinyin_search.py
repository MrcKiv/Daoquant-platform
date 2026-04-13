#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试拼音首字母搜索功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_main'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from stock_analysis.views import search_stocks

def test_pinyin_search():
    """测试拼音首字母搜索功能"""
    print("🚀 开始测试拼音首字母搜索功能...")
    
    # 测试用例
    test_cases = [
        "zg",      # 中国
        "zgsy",    # 中国石油
        "zgsh",    # 中国石化
        "zgyd",    # 中国移动
        "zgdx",    # 中国电信
        "zggh",    # 中国国航
        "zgjt",    # 中国交建
        "zgjs",    # 中国建筑
        "zgjg",    # 中国交建
        "zgny",    # 中国农业
        "zgzx",    # 中国中行
        "zgjt",    # 中国交建
        "zgjs",    # 中国建设
        "zggh",    # 中国国航
        "zgdx",    # 中国电信
        "zgyd",    # 中国移动
        "zgsh",    # 中国石化
        "zgsy",    # 中国石油
    ]
    
    for query in test_cases:
        print(f"\n🔍 测试搜索: {query}")
        try:
            results = search_stocks(query, limit=10)
            if results:
                print(f"✅ 找到 {len(results)} 个结果:")
                for i, stock in enumerate(results[:5], 1):  # 只显示前5个
                    print(f"  {i}. {stock['name']} ({stock['st_code']}) - {stock['industry']}")
                if len(results) > 5:
                    print(f"  ... 还有 {len(results) - 5} 个结果")
            else:
                print(f"❌ 未找到结果")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    
    print("\n🎯 测试完成!")

if __name__ == "__main__":
    test_pinyin_search()
