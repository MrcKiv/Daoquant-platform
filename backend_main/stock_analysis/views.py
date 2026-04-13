from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pymysql
from pypinyin import lazy_pinyin
import re
from backend.env import get_pymysql_config

# 数据库连接配置
DB_CONFIG = get_pymysql_config(charset='utf8')

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def search_stocks(query, limit=20):
    """综合搜索股票 - 从股票基本信息表获取基本信息"""
    conn = get_db_connection()
    try:
        # 构建搜索条件
        conditions = []
        params = []
        
        # 股票代码搜索（前缀匹配）
        if re.match(r'^\d{6}$', query):
            conditions.append("st_code LIKE %s")
            params.append(f"{query}%")
        
        # 股票名称搜索（模糊匹配）
        conditions.append("name LIKE %s")
        params.append(f"%{query}%")
        
        # 行业搜索
        conditions.append("industry LIKE %s")
        params.append(f"%{query}%")
        
        # 地区搜索
        conditions.append("area LIKE %s")
        params.append(f"%{query}%")
        
        # 拼音首字母搜索
        if re.match(r'^[a-zA-Z]+$', query):
            # 获取所有股票名称，进行拼音首字母匹配
            sql_all = "SELECT st_code, name, industry, area, market FROM `股票基本信息remove`"
            df_all = pd.read_sql(sql_all, conn)
            
            # 过滤匹配拼音首字母的股票
            matched_stocks = []
            for _, row in df_all.iterrows():
                stock_name = str(row['name'])
                if stock_name and stock_name != 'nan':
                    # 获取股票名称的拼音首字母
                    pinyin_initials = ''.join([p[0].lower() for p in lazy_pinyin(stock_name) if p])
                    # 检查是否匹配（支持前缀匹配）
                    if pinyin_initials.startswith(query.lower()):
                        matched_stocks.append(row.to_dict())
                        if len(matched_stocks) >= limit:
                            break
            
            return matched_stocks
        
        # 如果条件为空，添加默认搜索
        if not conditions:
            conditions.append("name LIKE %s")
            params.append(f"%{query}%")
        
        # 从股票基本信息表查询
        sql = f"""
        SELECT DISTINCT 
            st_code,
            name,
            industry,
            area,
            market
        FROM `股票基本信息remove`
        WHERE {' OR '.join(conditions)}
        LIMIT {limit}
        """
        
        df = pd.read_sql(sql, conn, params=params)
        return df.to_dict('records')
    finally:
        conn.close()

def get_stock_basic_info(stock_code):
    """获取股票基本信息"""
    conn = get_db_connection()
    try:
        sql = "SELECT * FROM `股票基本信息remove` WHERE st_code = %s"
        df = pd.read_sql(sql, conn, params=[stock_code])
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    finally:
        conn.close()

def get_stock_latest_quote(stock_code):
    """获取股票最新行情数据"""
    conn = get_db_connection()
    try:
        # 股票代码格式转换：如果只有6位数字，尝试添加市场后缀
        formatted_stock_code = stock_code
        if re.match(r'^\d{6}$', stock_code):
            # 先尝试查询基本信息表，获取正确的股票代码格式
            sql_check = "SELECT st_code FROM `股票基本信息remove` WHERE symbol = %s LIMIT 1"
            df_check = pd.read_sql(sql_check, conn, params=[stock_code])
            if not df_check.empty:
                formatted_stock_code = df_check.iloc[0]['st_code']
        
        # 获取最新的行情数据
        sql = """
        SELECT 
            st_code,
            close as latest_price,
            pct_chg as latest_change,
            vol as latest_volume,
            trade_date as latest_date,
            macd_macd as latest_macd,
            rsv as latest_rsi,
            kdj_k as latest_kdj_k,
            kdj_d as latest_kdj_d,
            boll_boll as latest_boll,
            cci as latest_cci,
            open, high, low, close
        FROM partition_table 
        WHERE st_code = %s 
        AND trade_date = (
            SELECT MAX(trade_date) 
            FROM partition_table 
            WHERE st_code = %s
        )
        """
        
        df = pd.read_sql(sql, conn, params=[formatted_stock_code, formatted_stock_code])
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    finally:
        conn.close()

def get_stock_daily_data(stock_code, days=120):
    """获取股票日线数据"""
    conn = get_db_connection()
    try:
        # 股票代码格式转换：如果只有6位数字，尝试添加市场后缀
        formatted_stock_code = stock_code
        if re.match(r'^\d{6}$', stock_code):
            # 先尝试查询基本信息表，获取正确的股票代码格式
            sql_check = "SELECT st_code FROM `股票基本信息remove` WHERE symbol = %s LIMIT 1"
            df_check = pd.read_sql(sql_check, conn, params=[stock_code])
            if not df_check.empty:
                formatted_stock_code = df_check.iloc[0]['st_code']
        
        # 获取最近N天的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        sql = """
        SELECT * FROM partition_table 
        WHERE st_code = %s AND trade_date BETWEEN %s AND %s
        ORDER BY trade_date ASC
        """
        
        df = pd.read_sql(sql, conn, params=[formatted_stock_code, start_date, end_date])
        return df
    finally:
        conn.close()

def get_index_data():
    """获取主要指数数据"""
    conn = get_db_connection()
    try:
        # 获取上证综指、深证成指、创业板指等主要指数
        sql = """
        SELECT * FROM `大盘指数_new` 
        WHERE st_code IN ('000001.SH', '399001.SZ', '399006.SZ')
        ORDER BY trade_date DESC
        LIMIT 90
        """
        
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def get_index_daily_data(st_code, days=120):
    """获取指数历史日线数据"""
    conn = get_db_connection()
    try:
        # 从大盘指数_new表获取数据（与get_index_data保持一致）
        sql = """
        SELECT * FROM `大盘指数_new` 
        WHERE st_code = %s
        ORDER BY trade_date DESC
        LIMIT %s
        """
        
        df = pd.read_sql(sql, conn, params=[st_code, days])
        print("df from 大盘指数_new:", len(df))
        # 如果大盘指数_new表没有数据，尝试从大盘指数表获取
        if df.empty:
            sql_old = """
            SELECT * FROM `大盘指数` 
            WHERE st_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            df = pd.read_sql(sql_old, conn, params=[st_code, days])
        
        # 按日期正序排列（从早到晚）
        if not df.empty:
            df = df.sort_values('trade_date').reset_index(drop=True)
        
        return df
    finally:
        conn.close()

def calculate_technical_indicators(df):
    """计算技术指标 - 使用数据库中已有的指标，补充计算缺失的指标"""
    if df.empty:
        return df
    
    # 确保数据类型正确
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
    
    # 使用数据库中已有的技术指标（如果存在）
    if 'macd_dif' in df.columns:
        df['macd'] = pd.to_numeric(df['macd_dif'], errors='coerce')
    if 'macd_dea' in df.columns:
        df['macd_signal'] = pd.to_numeric(df['macd_dea'], errors='coerce')
    if 'macd_macd' in df.columns:
        df['macd_histogram'] = pd.to_numeric(df['macd_macd'], errors='coerce')
    if 'rsv' in df.columns:
        df['rsi'] = pd.to_numeric(df['rsv'], errors='coerce')  # 使用RSV作为RSI
    if 'boll_boll' in df.columns:
        df['boll_middle'] = pd.to_numeric(df['boll_boll'], errors='coerce')
    if 'boll_ub' in df.columns:
        df['boll_upper'] = pd.to_numeric(df['boll_ub'], errors='coerce')
    if 'boll_lb' in df.columns:
        df['boll_lower'] = pd.to_numeric(df['boll_lb'], errors='coerce')
    
    # 补充计算移动平均线
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # 如果数据库中没有RSI，则计算
    if 'rsi' not in df.columns or df['rsi'].isna().all():
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
    
    # 如果数据库中没有布林带，则计算
    if 'boll_middle' not in df.columns or df['boll_middle'].isna().all():
        df['boll_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['boll_upper'] = df['boll_middle'] + (bb_std * 2)
        df['boll_lower'] = df['boll_middle'] - (bb_std * 2)
    
    # 如果数据库中没有MACD相关指标，则计算
    if 'macd' not in df.columns or df['macd'].isna().all():
        # 计算EMA
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    return df

def generate_stock_diagnosis(stock_code):
    """生成股票诊断结果"""
    # 获取股票数据
    df = get_stock_daily_data(stock_code, days=120)
    if df.empty:
        return None
    
    # 计算技术指标
    df = calculate_technical_indicators(df)
    
    # 获取最新数据
    latest = df.iloc[-1]
    prev_5 = df.iloc[-6:-1] if len(df) >= 6 else df
    prev_20 = df.iloc[-21:-1] if len(df) >= 21 else df
    
    # 技术面分析
    technical_score = 0
    technical_analysis = []
    
    # 价格趋势分析
    if latest['close'] > latest['ma20']:
        technical_score += 20
        technical_analysis.append("股价位于20日均线之上，短期趋势向好")
    else:
        technical_analysis.append("股价位于20日均线之下，短期趋势偏弱")
    
    # MACD分析
    if latest['macd'] > latest['macd_signal']:
        technical_score += 15
        technical_analysis.append("MACD金叉，技术面转强")
    else:
        technical_analysis.append("MACD死叉，技术面转弱")
    
    # RSI分析
    if 30 < latest['rsi'] < 70:
        technical_score += 15
        technical_analysis.append("RSI处于正常区间，无超买超卖")
    elif latest['rsi'] < 30:
        technical_score += 10
        technical_analysis.append("RSI超卖，可能存在反弹机会")
    else:
        technical_analysis.append("RSI超买，注意回调风险")
    
    # 成交量分析
    avg_vol = prev_20['vol'].mean()
    if latest['vol'] > avg_vol * 1.5:
        technical_score += 10
        technical_analysis.append("成交量放大，交投活跃")
    elif latest['vol'] < avg_vol * 0.5:
        technical_analysis.append("成交量萎缩，交投清淡")
    
    # 布林带分析
    if latest['close'] > latest['boll_upper']:
        technical_analysis.append("股价触及布林带上轨，注意回调风险")
    elif latest['close'] < latest['boll_lower']:
        technical_score += 10
        technical_analysis.append("股价触及布林带下轨，可能存在反弹机会")
    
    # 基本面分析（简化版）
    fundamental_score = 50  # 基础分
    fundamental_analysis = ["基本面分析需要更多财务数据支持"]
    
    # 综合评分
    overall_score = (technical_score + fundamental_score) // 2
    
    # 投资建议
    if overall_score >= 70:
        recommendation = "买入"
    elif overall_score >= 50:
        recommendation = "持有"
    else:
        recommendation = "卖出"
    
    # 风险等级
    if overall_score >= 70:
        risk_level = "低风险"
    elif overall_score >= 50:
        risk_level = "中等风险"
    else:
        risk_level = "高风险"
    
    return {
        'technical_score': technical_score,
        'technical_analysis': technical_analysis,
        'fundamental_score': fundamental_score,
        'fundamental_analysis': fundamental_analysis,
        'overall_score': overall_score,
        'recommendation': recommendation,
        'risk_level': risk_level,
        'risk_factors': ["市场风险", "行业风险", "个股风险"]
    }

# API接口
@csrf_exempt
@require_http_methods(["GET"])
def search_stocks_api(request):
    """股票搜索API"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'error': '搜索关键词不能为空'}, status=400)
    
    try:
        results = search_stocks(query)
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_info_api(request, code):
    """获取股票信息API"""
    stock_code = code
    if not stock_code:
        return JsonResponse({'error': '股票代码不能为空'}, status=400)
    
    try:
        # 基本信息
        basic_info = get_stock_basic_info(stock_code)
        if not basic_info:
            return JsonResponse({'error': '股票不存在'}, status=404)
        
        # 最新行情数据
        latest_quote = get_stock_latest_quote(stock_code)
        
        # 历史日线数据
        daily_data = get_stock_daily_data(stock_code, days=30)
        
        # 诊断结果
        diagnosis = generate_stock_diagnosis(stock_code)
        
        return JsonResponse({
            'basic_info': basic_info,
            'latest_quote': latest_quote,
            'daily_data': daily_data.to_dict('records') if not daily_data.empty else [],
            'diagnosis': diagnosis
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_index_data_api(request):
    """获取指数数据API"""
    try:
        index_data = get_index_data()
        return JsonResponse({
            'index_data': index_data.to_dict('records') if not index_data.empty else []
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_index_chart_data_api(request, st_code):
    """获取特定指数图表数据API"""
    if not st_code:
        return JsonResponse({'error': '指数代码不能为空'}, status=400)
    
    try:
        # 获取指数历史数据
        index_data = get_index_daily_data(st_code, days=120)
        if index_data.empty:
            return JsonResponse({'error': '无数据'}, status=404)
        
        # 计算技术指标
        index_data = calculate_technical_indicators(index_data)
        
        # 清理NaN值，将NaN替换为None（在JSON中会变成null）
        def clean_nan_values(series):
            """清理NaN值，将NaN替换为None"""
            return [None if pd.isna(x) else x for x in series.tolist()]
        
        # 准备图表数据 - 只包含存在的列
        chart_data = {
            'dates': index_data['trade_date'].tolist(),
            'prices': {
                'open': clean_nan_values(index_data['open']),
                'high': clean_nan_values(index_data['high']),
                'low': clean_nan_values(index_data['low']),
                'close': clean_nan_values(index_data['close'])
            },
            'volume': clean_nan_values(index_data['vol']),
            'indicators': {}
        }
        
        # 安全地添加技术指标，只添加存在的列
        if 'ma5' in index_data.columns:
            chart_data['indicators']['ma5'] = clean_nan_values(index_data['ma5'])
        if 'ma10' in index_data.columns:
            chart_data['indicators']['ma10'] = clean_nan_values(index_data['ma10'])
        if 'ma20' in index_data.columns:
            chart_data['indicators']['ma20'] = clean_nan_values(index_data['ma20'])
        if 'ma60' in index_data.columns:
            chart_data['indicators']['ma60'] = clean_nan_values(index_data['ma60'])
        if 'rsi' in index_data.columns:
            chart_data['indicators']['rsi'] = clean_nan_values(index_data['rsi'])
        if 'macd' in index_data.columns:
            chart_data['indicators']['macd'] = clean_nan_values(index_data['macd'])
        if 'macd_signal' in index_data.columns:
            chart_data['indicators']['macd_signal'] = clean_nan_values(index_data['macd_signal'])
        if 'macd_histogram' in index_data.columns:
            chart_data['indicators']['macd_histogram'] = clean_nan_values(index_data['macd_histogram'])
        if 'boll_upper' in index_data.columns:
            chart_data['indicators']['boll_upper'] = clean_nan_values(index_data['boll_upper'])
        if 'boll_middle' in index_data.columns:
            chart_data['indicators']['boll_middle'] = clean_nan_values(index_data['boll_middle'])
        if 'boll_lower' in index_data.columns:
            chart_data['indicators']['boll_lower'] = clean_nan_values(index_data['boll_lower'])
        
        return JsonResponse(chart_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_chart_data_api(request, code):
    """获取股票图表数据API"""
    stock_code = code
    period = request.GET.get('period', 'daily')  # daily, weekly, monthly
    days = int(request.GET.get('days', 120))
    
    if not stock_code:
        return JsonResponse({'error': '股票代码不能为空'}, status=400)
    
    try:
        daily_data = get_stock_daily_data(stock_code, days=days)
        if daily_data.empty:
            return JsonResponse({'error': '无数据'}, status=404)
        
        # 计算技术指标
        daily_data = calculate_technical_indicators(daily_data)
        
        # 清理NaN值，将NaN替换为None（在JSON中会变成null）
        def clean_nan_values(series):
            """清理NaN值，将NaN替换为None"""
            return [None if pd.isna(x) else x for x in series.tolist()]
        
        # 准备图表数据
        chart_data = {
            'dates': daily_data['trade_date'].tolist(),
            'prices': {
                'open': clean_nan_values(daily_data['open']),
                'high': clean_nan_values(daily_data['high']),
                'low': clean_nan_values(daily_data['low']),
                'close': clean_nan_values(daily_data['close'])
            },
            'volume': clean_nan_values(daily_data['vol']),
            'indicators': {
                'ma5': clean_nan_values(daily_data['ma5']),
                'ma10': clean_nan_values(daily_data['ma10']),
                'ma20': clean_nan_values(daily_data['ma20']),
                'ma60': clean_nan_values(daily_data['ma60']),
                'rsi': clean_nan_values(daily_data['rsi']),
                'macd': clean_nan_values(daily_data['macd']),
                'macd_signal': clean_nan_values(daily_data['macd_signal']),
                'macd_histogram': clean_nan_values(daily_data['macd_histogram']),
                'boll_upper': clean_nan_values(daily_data['boll_upper']),
                'boll_middle': clean_nan_values(daily_data['boll_middle']),
                'boll_lower': clean_nan_values(daily_data['boll_lower'])
            }
        }
        # print('this is chart_data', chart_data)
        
        return JsonResponse(chart_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
