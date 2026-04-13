#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复后的股票代码格式转换功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_main'))

import pymysql
import pandas as pd

# 数据库连接配置
DB_CONFIG = {
    'host': '192.168.6.243',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'jdgp',
    'charset': 'utf8'
}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def test_stock_code_conversion():
    """测试股票代码格式转换功能"""
    conn = get_db_connection()
    try:
        print("🔍 测试股票代码格式转换功能...")
        
        # 测试不同的股票代码格式
        test_codes = ['000001', '000001.SZ', '000002', '000002.SZ']
        
        for test_code in test_codes:
            print(f"\n测试代码: {test_code}")
            
            # 1. 测试基本信息查询
            sql1 = "SELECT * FROM `股票基本信息remove` WHERE st_code = %s OR symbol = %s"
            df1 = pd.read_sql(sql1, conn, params=[test_code, test_code])
            print(f"  基本信息查询结果: {len(df1)} 条记录")
            if not df1.empty:
                print(f"  基本信息: {df1[['st_code', 'symbol', 'name']].iloc[0].to_dict()}")
            
            # 2. 测试行情数据查询（模拟修复后的逻辑）
            formatted_stock_code = test_code
            if len(test_code) == 6 and test_code.isdigit():
                # 模拟修复后的逻辑：通过symbol查找st_code
                sql_check = "SELECT st_code FROM `股票基本信息remove` WHERE symbol = %s LIMIT 1"
                df_check = pd.read_sql(sql_check, conn, params=[test_code])
                if not df_check.empty:
                    formatted_stock_code = df_check.iloc[0]['st_code']
                    print(f"  代码格式转换: {test_code} -> {formatted_stock_code}")
            
            # 查询partition_table
            sql2 = """
            SELECT COUNT(*) as count 
            FROM partition_table 
            WHERE st_code = %s
            """
            df2 = pd.read_sql(sql2, conn, params=[formatted_stock_code])
            print(f"  行情数据查询结果: {df2.iloc[0]['count']} 条记录")
            
            # 3. 测试最新行情数据
            sql3 = """
            SELECT 
                st_code,
                close as latest_price,
                pct_chg as latest_change,
                vol as latest_volume,
                trade_date as latest_date
            FROM partition_table 
            WHERE st_code = %s 
            AND trade_date = (
                SELECT MAX(trade_date) 
                FROM partition_table 
                WHERE st_code = %s
            )
            """
            
            df3 = pd.read_sql(sql3, conn, params=[formatted_stock_code, formatted_stock_code])
            if not df3.empty:
                latest_data = df3.iloc[0]
                print(f"  最新行情: 价格={latest_data['latest_price']}, 涨跌幅={latest_data['latest_change']}%, 成交量={latest_data['latest_volume']}, 日期={latest_data['latest_date']}")
            else:
                print("  未找到最新行情数据")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        conn.close()

def test_frontend_integration():
    """测试前端集成场景"""
    conn = get_db_connection()
    try:
        print("\n🔍 测试前端集成场景...")
        
        # 模拟前端传入000001的情况
        frontend_code = '000001'
        print(f"前端传入的股票代码: {frontend_code}")
        
        # 1. 获取基本信息
        sql1 = "SELECT * FROM `股票基本信息remove` WHERE symbol = %s"
        df1 = pd.read_sql(sql1, conn, params=[frontend_code])
        if not df1.empty:
            basic_info = df1.iloc[0]
            print(f"基本信息: {basic_info[['st_code', 'symbol', 'name', 'industry', 'area']].to_dict()}")
            
            # 2. 获取最新行情（使用转换后的代码）
            formatted_code = basic_info['st_code']
            sql2 = """
            SELECT 
                st_code,
                close as latest_price,
                pct_chg as latest_change,
                vol as latest_volume,
                trade_date as latest_date,
                macd_macd, rsv, kdj_k, kdj_d, boll_boll, cci
            FROM partition_table 
            WHERE st_code = %s 
            AND trade_date = (
                SELECT MAX(trade_date) 
                FROM partition_table 
                WHERE st_code = %s
            )
            """
            
            df2 = pd.read_sql(sql2, conn, params=[formatted_code, formatted_code])
            if not df2.empty:
                latest_quote = df2.iloc[0]
                print(f"最新行情: 价格={latest_quote['latest_price']}, 涨跌幅={latest_quote['latest_change']}%")
                print(f"技术指标: MACD={latest_quote['macd_macd']}, RSI={latest_quote['rsv']}, KDJ_K={latest_quote['kdj_k']}")
            
            # 3. 获取日线数据
            sql3 = """
            SELECT trade_date, open, high, low, close, vol 
            FROM partition_table 
            WHERE st_code = %s 
            ORDER BY trade_date DESC 
            LIMIT 5
            """
            
            df3 = pd.read_sql(sql3, conn, params=[formatted_code])
            print(f"日线数据: 获取到 {len(df3)} 条记录")
            if not df3.empty:
                print("最近5天数据:")
                for _, row in df3.iterrows():
                    print(f"  {row['trade_date']}: 开{row['open']} 高{row['high']} 低{row['low']} 收{row['close']} 量{row['vol']}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 开始测试修复后的股票代码格式转换功能...")
    
    test_stock_code_conversion()
    test_frontend_integration()
    
    print("\n✅ 测试完成!")

