#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个股诊断模块测试脚本
用于验证模块的基本功能是否正常
"""

import sys
import os
import django

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from stock_analysis.views import (
    get_db_connection, 
    search_stocks, 
    get_stock_basic_info,
    get_stock_daily_data,
    get_index_data,
    calculate_technical_indicators,
    generate_stock_diagnosis
)

def test_database_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    try:
        conn = get_db_connection()
        print("✓ 数据库连接成功")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False

def test_search_stocks():
    """测试股票搜索功能"""
    print("\n测试股票搜索功能...")
    try:
        # 测试股票代码搜索
        results = search_stocks("000001", limit=5)
        print(f"✓ 股票代码搜索成功，找到 {len(results)} 个结果")
        
        # 测试股票名称搜索
        results = search_stocks("平安", limit=5)
        print(f"✓ 股票名称搜索成功，找到 {len(results)} 个结果")
        
        return True
    except Exception as e:
        print(f"✗ 股票搜索失败: {e}")
        return False

def test_get_stock_info():
    """测试获取股票信息"""
    print("\n测试获取股票信息...")
    try:
        # 测试获取平安银行信息
        stock_info = get_stock_basic_info("000001")
        if stock_info:
            print(f"✓ 获取股票信息成功: {stock_info.get('name', 'Unknown')}")
        else:
            print("✗ 未找到股票信息")
            return False
        return True
    except Exception as e:
        print(f"✗ 获取股票信息失败: {e}")
        return False

def test_get_stock_data():
    """测试获取股票数据"""
    print("\n测试获取股票数据...")
    try:
        # 测试获取平安银行日线数据
        daily_data = get_stock_daily_data("000001", days=30)
        if not daily_data.empty:
            print(f"✓ 获取股票数据成功，共 {len(daily_data)} 条记录")
            print(f"  最新日期: {daily_data.iloc[-1]['trade_date']}")
            print(f"  最新收盘价: {daily_data.iloc[-1]['close']}")
        else:
            print("✗ 未找到股票数据")
            return False
        return True
    except Exception as e:
        print(f"✗ 获取股票数据失败: {e}")
        return False

def test_get_index_data():
    """测试获取指数数据"""
    print("\n测试获取指数数据...")
    try:
        index_data = get_index_data()
        if not index_data.empty:
            print(f"✓ 获取指数数据成功，共 {len(index_data)} 条记录")
            print(f"  指数代码: {index_data['ts_code'].unique()}")
        else:
            print("✗ 未找到指数数据")
            return False
        return True
    except Exception as e:
        print(f"✗ 获取指数数据失败: {e}")
        return False

def test_technical_indicators():
    """测试技术指标计算"""
    print("\n测试技术指标计算...")
    try:
        # 获取测试数据
        daily_data = get_stock_daily_data("000001", days=60)
        if daily_data.empty:
            print("✗ 无法获取测试数据")
            return False
        
        # 计算技术指标
        df_with_indicators = calculate_technical_indicators(daily_data)
        
        # 检查是否计算了必要的指标
        required_indicators = ['ma5', 'ma10', 'ma20', 'rsi', 'macd']
        missing_indicators = []
        
        for indicator in required_indicators:
            if indicator not in df_with_indicators.columns:
                missing_indicators.append(indicator)
        
        if missing_indicators:
            print(f"✗ 缺少技术指标: {missing_indicators}")
            return False
        
        print("✓ 技术指标计算成功")
        print(f"  MA5: {df_with_indicators['ma5'].iloc[-1]:.2f}")
        print(f"  MA20: {df_with_indicators['ma20'].iloc[-1]:.2f}")
        print(f"  RSI: {df_with_indicators['rsi'].iloc[-1]:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ 技术指标计算失败: {e}")
        return False

def test_stock_diagnosis():
    """测试股票诊断功能"""
    print("\n测试股票诊断功能...")
    try:
        # 生成股票诊断结果
        diagnosis = generate_stock_diagnosis("000001")
        if diagnosis:
            print("✓ 股票诊断成功")
            print(f"  技术面评分: {diagnosis['technical_score']}")
            print(f"  综合评分: {diagnosis['overall_score']}")
            print(f"  投资建议: {diagnosis['recommendation']}")
            print(f"  风险等级: {diagnosis['risk_level']}")
            print(f"  技术分析: {len(diagnosis['technical_analysis'])} 条")
        else:
            print("✗ 股票诊断失败")
            return False
        return True
    except Exception as e:
        print(f"✗ 股票诊断失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("个股诊断模块功能测试")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_search_stocks,
        test_get_stock_info,
        test_get_stock_data,
        test_get_index_data,
        test_technical_indicators,
        test_stock_diagnosis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ 测试执行异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！模块功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

