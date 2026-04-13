#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试指数去重逻辑
"""

def test_index_deduplication():
    """测试指数去重逻辑"""
    print("🧪 测试指数去重逻辑...")
    
    # 模拟重复的指数数据
    mock_index_data = [
        {'ts_code': '000001.SZ', 'name': '上证综指', 'close': 2837.43, 'pct_chg': 0.05},
        {'ts_code': '000001.SH', 'name': '上证综指', 'close': 2837.43, 'pct_chg': 0.05},  # 重复
        {'ts_code': '000300.SH', 'name': '沪深300', 'close': 3200.12, 'pct_chg': -0.41},
        {'ts_code': '399001.SZ', 'name': '深证成指', 'close': 8078.82, 'pct_chg': -0.41},
        {'ts_code': '399001.SZ', 'name': '深证成指', 'close': 8078.82, 'pct_chg': -0.41},  # 重复
        {'ts_code': '399006.SZ', 'name': '创业板指', 'close': 1531.45, 'pct_chg': 0.05},
        {'ts_code': '000688.SH', 'name': '科创板50', 'close': 1250.67, 'pct_chg': 0.16},
        {'ts_code': '000016.SH', 'name': '上证50', 'close': 2150.89, 'pct_chg': -0.23},
        {'ts_code': '000905.SH', 'name': '中证500', 'close': 1850.34, 'pct_chg': 0.12},
        {'ts_code': '000852.SH', 'name': '中证1000', 'close': 1650.78, 'pct_chg': -0.18},
        {'ts_code': '000001.SH', 'name': '上证综指', 'close': 2837.43, 'pct_chg': 0.05},  # 再次重复
    ]
    
    print(f"原始数据: {len(mock_index_data)} 条记录")
    for i, index in enumerate(mock_index_data):
        print(f"  {i+1}. {index['ts_code']} - {index['name']}")
    
    # 去重逻辑（模拟前端JavaScript逻辑）
    unique_index_data = []
    seen_codes = set()
    
    # 按ts_code分组，保留最新的数据
    for index in mock_index_data:
        if index['ts_code'] not in seen_codes:
            seen_codes.add(index['ts_code'])
            unique_index_data.append(index)
    
    print(f"\n去重后: {len(unique_index_data)} 条记录")
    for i, index in enumerate(unique_index_data):
        print(f"  {i+1}. {index['ts_code']} - {index['name']}")
    
    # 按重要性排序
    priority_order = [
        '000001.SH', # 上证综指
        '000300.SH', # 沪深300
        '399001.SZ', # 深证成指
        '399006.SZ', # 创业板指
        '000688.SH', # 科创板50
        '000016.SH', # 上证50
        '000905.SH', # 中证500
        '000852.SH'  # 中证1000
    ]
    
    def sort_by_priority(a, b):
        a_priority = priority_order.index(a['ts_code']) if a['ts_code'] in priority_order else -1
        b_priority = priority_order.index(b['ts_code']) if b['ts_code'] in priority_order else -1
        
        # 如果都在优先级列表中，按优先级排序
        if a_priority != -1 and b_priority != -1:
            return a_priority - b_priority
        # 如果只有一个在优先级列表中，优先级高的排在前面
        if a_priority != -1:
            return -1
        if b_priority != -1:
            return 1
        # 都不在优先级列表中，按ts_code排序
        return a['ts_code'].compare(b['ts_code'])
    
    # 排序
    unique_index_data.sort(key=lambda x: priority_order.index(x['ts_code']) if x['ts_code'] in priority_order else 999)
    
    print(f"\n排序后:")
    for i, index in enumerate(unique_index_data):
        priority = priority_order.index(index['ts_code']) if index['ts_code'] in priority_order else 'N/A'
        print(f"  {i+1}. {index['ts_code']} - {index['name']} (优先级: {priority})")
    
    # 限制显示数量
    display_limit = 8
    display_data = unique_index_data[:display_limit]
    
    print(f"\n显示前{display_limit}个指数:")
    for i, index in enumerate(display_data):
        print(f"  {i+1}. {index['ts_code']} - {index['name']}")
    
    if len(unique_index_data) > display_limit:
        print(f"  还有 {len(unique_index_data) - display_limit} 个指数未显示")
    
    print(f"\n✅ 去重测试完成!")
    print(f"  原始数据: {len(mock_index_data)} 条")
    print(f"  去重后: {len(unique_index_data)} 条")
    print(f"  显示数量: {len(display_data)} 条")
    
    return {
        'original_count': len(mock_index_data),
        'unique_count': len(unique_index_data),
        'display_count': len(display_data),
        'duplicates_removed': len(mock_index_data) - len(unique_index_data)
    }

def test_priority_sorting():
    """测试优先级排序逻辑"""
    print(f"\n🔍 测试优先级排序逻辑...")
    
    test_codes = [
        '000001.SH', '000300.SH', '399001.SZ', '399006.SZ',
        '000688.SH', '000016.SH', '000905.SH', '000852.SH',
        'OTHER1.SH', 'OTHER2.SZ'  # 不在优先级列表中的代码
    ]
    
    priority_order = [
        '000001.SH', '000300.SH', '399001.SZ', '399006.SZ',
        '000688.SH', '000016.SH', '000905.SH', '000852.SH'
    ]
    
    # 模拟排序逻辑
    sorted_codes = sorted(test_codes, key=lambda x: priority_order.index(x) if x in priority_order else 999)
    
    print("排序结果:")
    for i, code in enumerate(sorted_codes):
        if code in priority_order:
            priority = priority_order.index(code)
            print(f"  {i+1}. {code} (优先级: {priority})")
        else:
            print(f"  {i+1}. {code} (无优先级)")
    
    return sorted_codes

if __name__ == "__main__":
    # 测试去重逻辑
    dedup_result = test_index_deduplication()
    
    # 测试优先级排序
    sort_result = test_priority_sorting()
    
    print(f"\n🎯 总结:")
    print(f"  去重效果: 移除了 {dedup_result['duplicates_removed']} 个重复记录")
    print(f"  显示优化: 只显示前 {dedup_result['display_count']} 个主要指数")
    print(f"  排序逻辑: 按重要性优先级排序，重要指数优先显示")

