from sqlalchemy import create_engine, text

import os
import datetime
import pymysql as mdb
import pandas as pd
from backend.env import get_pymysql_config, get_sqlalchemy_database_url

# =========================
# SQLAlchemy Engine（查询专用）
# =========================
ENGINE = create_engine(
    get_sqlalchemy_database_url(charset="utf8mb4"),
    pool_pre_ping=True,
    pool_recycle=3600,
)


def safe_read_sql(sql, params=None):
    """
    Runtime-safe unified SQL reader.

    Key guarantees:
    - SQL is always a string
    - Pandas always receives a raw DBAPI connection
    - Compatible with %s placeholders (PyMySQL style)
    - STRICTLY READ-ONLY: Forbids DELETE/INSERT/UPDATE
    """

    # 🔒 HARD GUARD: normalize SQL to string
    if not isinstance(sql, str):
        sql = str(sql)

    # 🛡️ SECURITY CHECK: Forbid write operations
    sql_upper = sql.upper().strip()
    # Simple keyword check (can be bypassed by complex SQL but sufficient for unintentional misuse)
    forbidden_keywords = ['DELETE ', 'INSERT ', 'UPDATE ', 'DROP ', 'ALTER ', 'TRUNCATE ', 'CREATE ']
    for kw in forbidden_keywords:
        if sql_upper.startswith(kw):
             raise ValueError(f"safe_read_sql forbids non-SELECT statements: {kw} detected in '{sql[:50]}...'")

    try:
        with ENGINE.connect() as conn:
            raw_conn = conn.connection  # DBAPI connection (has cursor)

            if params:
                return pd.read_sql(sql, raw_conn, params=params)

            return pd.read_sql(sql, raw_conn)
    except Exception as e:
        print(f"❌ safe_read_sql Error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty DataFrame on error to prevent crash
        return pd.DataFrame()


def query_sql(sql, params=None):
    return safe_read_sql(sql, params=params)


def deduplicate_rows(df, subset, label):
    """Remove duplicate business-key rows while keeping the existing loader flow."""
    if df is None or df.empty:
        return df

    subset = [col for col in subset if col in df.columns]
    if not subset:
        return df

    deduped = df.drop_duplicates(subset=subset, keep='first').reset_index(drop=True)
    removed = len(df) - len(deduped)
    if removed > 0:
        print(f"Deduplicated {label}: removed {removed} rows on {subset}")
    return deduped

# 连接MySQL数据库的全局变量
conn = None


def get_connection():
    """确保数据库连接有效，并返回连接"""
    global conn
    if conn is None or not conn.open:
        conn = mdb.connect(
            **get_pymysql_config(
                charset="utf8",
                connect_timeout=10,
                read_timeout=120,
                write_timeout=120,
            )
        )
    return conn


def get_cursor():
    """获取一个新的游标"""
    conn = get_connection()
    return conn.cursor()


def execute_sql(sql, params=None):
    """
    执行写操作 SQL (INSERT/UPDATE/DELETE)
    禁止使用 pd.read_sql
    """
    print(f"Executing Write SQL: {sql[:200]}..." if len(sql) > 200 else f"Executing SQL: {sql}")
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
    except mdb.MySQLError as e:
        print(f"Database error executing SQL: {e}")
        conn.rollback()
        raise



def query_sql_in_chunks(table_name, start_date_str, end_date_str, date_col='trade_date', extra_conditions='', chunk_years=1):
    """
    按年份分片读取数据，防止一次性读取过大导致 Connection Lost。
    """
    # 尝试解析日期格式
    try:
        if '-' in start_date_str:
            dt_start = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            dt_start = datetime.datetime.strptime(start_date_str, '%Y%m%d')

        if '-' in end_date_str:
            dt_end = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            dt_end = datetime.datetime.strptime(end_date_str, '%Y%m%d')
    except Exception as e:
        print(f"Chunks Date Parse Error: {e}")
        # 如果解析失败，回退到原始普通查询（风险自负）
        sql = f"SELECT * FROM {table_name} WHERE {date_col} BETWEEN '{start_date_str}' AND '{end_date_str}' {extra_conditions}"
        return query_sql(sql)

    all_dfs = []
    current_start = dt_start

    print(f"Start Chunking Reading {table_name} from {start_date_str} to {end_date_str} ...")

    while current_start <= dt_end:
        # Use 30 days chunk to prevent packet size frame issues
        current_end = current_start + datetime.timedelta(days=30)
        
        if current_end > dt_end:
            current_end = dt_end

        s_str = current_start.strftime('%Y%m%d')
        e_str = current_end.strftime('%Y%m%d')
        
        # 针对 60分钟线等可能有不同日期格式的情况，这里统一传参给 query_sql，依赖其内部 pymysql 的处理
        # 或者我们显式构建 SQL
        if '-' in start_date_str: # 如果原输入是带横杠的，保持一致
             s_str = current_start.strftime('%Y-%m-%d')
             e_str = current_end.strftime('%Y-%m-%d')

        print(f"  -> Reading chunk: {s_str} to {e_str}")
        
        # 构造 SQL
        # 注意：这里我们假设 select *，如果需要特定字段，需要进一步封装。
        # 目前主要针对 database() 函数里那种整表读取。
        # 对于 stock_60m，它的 select 字段较多，我们可能需要允许传入 select_clause
        
        select_clause = "SELECT *"
        if 'stock_60m' in table_name or 'stock_code' in extra_conditions: 
             # 简单的启发式兼容，或者我们在调用时不使用这个 helper，而是直接原地写循环。
             # 为了避免修改太大，我们让调用方稍后适配，或者简单地在这里做个判断?
             # 更好的方式是 parameterize select_clause
             pass

        sql = f"SELECT * FROM {table_name} WHERE {date_col} BETWEEN '{s_str}' AND '{e_str}' {extra_conditions}"
        
        # 如果是 stock_60m，我们在这一层无法知道具体的 SELECT 字段。
        # 必须修改函数签名以支持 select_clause
        
        chunk_df = query_sql(sql)
        if not chunk_df.empty:
            all_dfs.append(chunk_df)
        
        # 步进
        current_start = current_end + datetime.timedelta(days=1)

    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def query_custom_sql_in_chunks(sql_template, start_date_str, end_date_str, start_ph='%s', end_ph='%s', chunk_years=1):
    """
    针对已有的复杂 SQL 语句进行分片。
    sql_template: "SELECT ... FROM ... WHERE ... BETWEEN %s AND %s ..."
    """
    try:
        if '-' in start_date_str:
            dt_start = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            dt_start = datetime.datetime.strptime(start_date_str, '%Y%m%d')

        if '-' in end_date_str:
            dt_end = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            dt_end = datetime.datetime.strptime(end_date_str, '%Y%m%d')
    except:
         return query_sql(sql_template, params=(start_date_str, end_date_str))

    all_dfs = []
    current_start = dt_start
    print(f"Start Chunking Query... {start_date_str} - {end_date_str}")

    while current_start <= dt_end:
        # Use 30 days chunk
        current_end = current_start + datetime.timedelta(days=30)
        
        if current_end > dt_end:
            current_end = dt_end

        # 保持格式
        if '-' in start_date_str:
             s_str = current_start.strftime('%Y-%m-%d')
             e_str = current_end.strftime('%Y-%m-%d')
        else:
             s_str = current_start.strftime('%Y%m%d')
             e_str = current_end.strftime('%Y%m%d')
        
        print(f"  -> Chunk: {s_str} to {e_str}")
        
        # 注意：query_sql 的 params 是元组，会按顺序替换 %s
        # 假设模板里只有两个 %s 用于时间
        chunk_df = query_sql(sql_template, params=(s_str, e_str))
        
        if not chunk_df.empty:
            all_dfs.append(chunk_df)

        current_start = current_end + datetime.timedelta(days=1)

    if not all_dfs:
        return pd.DataFrame()
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def save_df(df, table_name, chunk_size=1000):
    """
    保存DataFrame到数据库，使用 execute_sql (pymysql) 替代 to_sql (sqlalchemy)
    以避免 OperationalError: Lost connection to MySQL server
    """
    if df is None or df.empty:
        print(f"Dataframe for {table_name} is empty, skipping save.")
        return

    # 处理 NaN 值，将其转换为 None，以便插入 NULL
    df = df.where(pd.notnull(df), None)

    cols = ",".join([f"`{k}`" for k in df.columns])
    placeholders = ",".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

    conn = get_connection()
    cursor = conn.cursor()

    total_rows = len(df)
    print(f"Saving {total_rows} rows to {table_name}...")

    try:
        for i in range(0, total_rows, chunk_size):
            chunk = df.iloc[i:i + chunk_size]
            data = chunk.values.tolist()
            cursor.executemany(sql, data)
            conn.commit()
            print(f"  -> Saved rows {i} to {min(i + chunk_size, total_rows)}")
    except Exception as e:
        print(f"Error saving to {table_name}: {e}")
        conn.rollback()
    finally:
        cursor.close()



def close_connection():
    """关闭数据库连接"""
    global conn
    if conn is not None:
        conn.close()
        conn = None


# 列出所有的数据表
table_calendar = "股票日历_new"
table_shareholding = "new_war_当前持股信息表"
table_transaction = "new_war_历史成交信息表"
table_statistic = "new_war_每日统计表"
table_daily_qfq_25before = "前复权日线行情_移动股池"
# table_daily_qfq_2025 = "partition_table"
table_daily_qfq_2025 = "partition_table"
# table_daily_qfq_2025 = "前复权日线行情_移动股池收盘数据"

table_stock_information = "股票基本信息remove"
table_macd_cross = "macd_cross_new"
table_baseline = "大盘盈亏表"
table_index = "大盘指数_new"
table_industry = "当日入选概念个股"
# table_labels = "股票标签"
table_labels = "股票标签_sby"
User_Strategy_Configuration = "用户策略配置表"
table_user_strategy_configuration = "用户策略配置表"
table_industry_status_history = "industry_status_history"
table_industry_stock = "当日入选概念个股"
stock_60m = "stock_60m_all"
# stock_60m = "200_股票池_table_60m"
stock_1d = "stock_1d_all"
table_st_stock = "st股票数据"
# DataFrames
df_table_calendar = None
# df_table_shareholding = None
df_table_shareholding = pd.DataFrame(columns=[
        'trade_date', 'st_code', 'number_of_securities', 'saleable_quantity',
        'cost_price', 'profit_and_loss', 'profit_and_loss_ratio', 'latest_value',
        'current_price', 'strategy_id', 'user_id'
    ])
# df_table_transaction = None
df_table_transaction = pd.DataFrame(columns=[
        'st_code', 'trade_date', 'trade_type', 'trade_price',
        'number_of_transactions', 'turnover', 'strategy_id', 'user_id'
    ])
# df_table_statistic = None
df_table_statistic =  pd.DataFrame(columns=[
        'trade_date', 'balance', 'available', 'reference_market_capitalization',
        'assets', 'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
    ])
df_table_daily_qfq = None
df_table_daily_qfq_25before = None
df_table_stock_information = None
df_table_macd_cross = None
df_table_baseline = None
df_table_index = None
df_table_industry = None
df_table_labels = None
df_table_user_strategy_configuration = None
df_table_industry_status_history = None
df_table_industry_stock = None
df_stock_60m = None
df_stock_1d = None
df_table_st_stock = None

def database(start_day, stop_day, sid, uid, Parameter):
    print(start_day)
    print(stop_day)
    print(sid)
    print(uid)

    sql1 = "SELECT * FROM {} WHERE cal_date between '{}' and '{}'".format(table_calendar, start_day, stop_day)
    global df_table_calendar
    df_table_calendar = query_sql(sql1)
    print("df_table_calendar:", df_table_calendar)
    print("df_table_calendar:", len(df_table_calendar))

    sql2 = f"SELECT * FROM {table_shareholding} WHERE user_id=%s AND strategy_id=%s"
    global df_table_shareholding
    df_table_shareholding = query_sql(sql2, params=(uid, sid))
    print("df_table_shareholding:", len(df_table_shareholding))

    sql3 = f"SELECT * FROM {table_transaction} WHERE user_id=%s AND strategy_id=%s"
    global df_table_transaction
    df_table_transaction = query_sql(sql3, params=(uid, sid))
    print("df_table_transaction:", len(df_table_transaction))

    sql4 = f"SELECT * FROM {table_statistic} WHERE user_id=%s AND strategy_id=%s"
    global df_table_statistic
    df_table_statistic = query_sql(sql4, params=(uid, sid))
    print("df_table_statistic:", len(df_table_statistic))
    # # print('11111111111111111111')

    global df_table_daily_qfq

    # # 判断日期范围，决定查询哪个表或合并查询
    # start_date_obj = datetime.datetime.strptime(start_day, '%Y%m%d')
    # print(1111)
    # cutoff_date = datetime.datetime(2025, 1, 1)
    # print(2222)
    # # 如果查询开始日期在2025年1月1日或之后，只查询table_daily_qfq_2025表
    # if start_date_obj >= cutoff_date:
    #     print(3333)
    #     sql4_5 = f"SELECT * FROM {table_daily_qfq_2025} WHERE trade_date BETWEEN %s AND %s"
    #     df_table_daily_qfq = query_sql(sql4_5, params=(start_day, stop_day))
    # # 如果查询开始日期在2025年1月1日之前，需要分表查询并合并
    # else:
    #     print(4444)
    #     # 查询2025年之前的数据表
    #     sql_before = f"SELECT * FROM {table_daily_qfq_25before} WHERE trade_date BETWEEN %s AND %s"
    #     # 查询截止日期为2024年12月31日或查询结束日期，取较早者
    #     cutoff_str = cutoff_date.strftime('%Y%m%d')
    #     end_before = min(cutoff_str, stop_day)
    #     df_table_daily_qfq_before = query_sql(sql_before, params=(start_day, end_before))
    #
    #     # 如果查询结束日期在2025年1月1日或之后，还需要查询2025年之后的数据表
    #     if stop_day >= cutoff_str:
    #         print(5555)
    #         sql_after = f"SELECT * FROM {table_daily_qfq_2025} WHERE trade_date BETWEEN %s AND %s"
    #         df_table_daily_qfq_after = query_sql(sql_after, params=(cutoff_str, stop_day))
    #         # 合并两个表的数据
    #         df_table_daily_qfq = pd.concat([df_table_daily_qfq_before, df_table_daily_qfq_after], ignore_index=True)
    #     else:
    #         df_table_daily_qfq = df_table_daily_qfq_before
    #
    # print("df_table_daily_qfq_数据库:", len(df_table_daily_qfq))
    # 判断日期范围，决定查询哪个表或合并查询
    try:
        # 处理不同格式的日期字符串
        if '-' in start_day:
            start_date_obj = datetime.datetime.strptime(start_day, '%Y-%m-%d')
        else:
            start_date_obj = datetime.datetime.strptime(start_day, '%Y%m%d')
        print(1111)
        cutoff_date = datetime.datetime(2025, 1, 1)
        print(2222)
        # 如果查询开始日期在2025年1月1日或之后，只查询table_daily_qfq_2025表
        if start_date_obj >= cutoff_date:
            print(3333)
            sql4_5 = f"SELECT * FROM {table_daily_qfq_2025} WHERE trade_date BETWEEN %s AND %s"
            # 改用分片读取
            # df_table_daily_qfq = query_sql(sql4_5, params=(start_day, stop_day))
            df_table_daily_qfq = query_custom_sql_in_chunks(sql4_5, start_day, stop_day)
        # 如果查询开始日期在2025年1月1日之前，需要分表查询并合并
        else:
            print(4444)
            # 查询2025年之前的数据表
            sql_before = f"SELECT * FROM {table_daily_qfq_25before} WHERE trade_date BETWEEN %s AND %s"
            # 查询截止日期为2024年12月31日或查询结束日期，取较早者
            cutoff_str = cutoff_date.strftime('%Y%m%d')
            cutoff_prev_str = (cutoff_date - datetime.timedelta(days=1)).strftime('%Y%m%d')
            # 确保stop_day格式一致
            if '-' in stop_day:
                stop_day_fmt = datetime.datetime.strptime(stop_day, '%Y-%m-%d').strftime('%Y%m%d')
            else:
                stop_day_fmt = stop_day
            end_before = min(cutoff_prev_str, stop_day_fmt)
            
            # 由于旧表 (例如 `前复权日线行情_移动股池`) 库中时间字段是带横杠的字符串，我们需要强行转换为 YYYY-MM-DD
            start_before_dash = start_date_obj.strftime('%Y-%m-%d')
            end_before_dash = datetime.datetime.strptime(end_before, '%Y%m%d').strftime('%Y-%m-%d')

            # 同样应用分片
            if start_before_dash <= end_before_dash:
                df_table_daily_qfq_before = query_custom_sql_in_chunks(sql_before, start_before_dash, end_before_dash)
            else:
                df_table_daily_qfq_before = pd.DataFrame()

            # 如果查询结束日期在2025年1月1日或之后，还需要查询2025年之后的数据表
            if stop_day_fmt >= cutoff_str:
                print(5555)
                sql_after = f"SELECT * FROM {table_daily_qfq_2025} WHERE trade_date BETWEEN %s AND %s"
                # 确保cutoff_str和stop_day格式一致
                # df_table_daily_qfq_after = query_sql(sql_after, params=(cutoff_str, stop_day_fmt))
                df_table_daily_qfq_after = query_custom_sql_in_chunks(sql_after, cutoff_str, stop_day_fmt)
                # 合并两个表的数据
                df_table_daily_qfq = pd.concat([df_table_daily_qfq_before, df_table_daily_qfq_after], ignore_index=True)
            else:
                df_table_daily_qfq = df_table_daily_qfq_before

    except Exception as e:
        print(f"日期处理出错: {e}")
        # 如果日期处理失败，默认查询新表
        sql_default = f"SELECT * FROM {table_daily_qfq_2025} WHERE trade_date BETWEEN %s AND %s"
        # df_table_daily_qfq = query_sql(sql_default, params=(start_day, stop_day))
        df_table_daily_qfq = query_custom_sql_in_chunks(sql_default, start_day, stop_day)

    print("df_table_daily_qfq_数据库:", len(df_table_daily_qfq))


    df_table_daily_qfq = deduplicate_rows(df_table_daily_qfq, ['trade_date', 'st_code'], 'df_table_daily_qfq')
    print(f"df_table_daily_qfq effective rows: {len(df_table_daily_qfq)}")

    sql7 = "SELECT * FROM {}".format(table_stock_information)
    global df_table_stock_information
    print("Loading table_stock_information...")
    df_table_stock_information = query_sql(sql7)

    sql8 = "SELECT * FROM {} WHERE trade_date between '{}' and '{}'".format(table_macd_cross, start_day, stop_day)
    global df_table_macd_cross
    print("Loading table_macd_cross...")
    df_table_macd_cross = query_sql(sql8)

    sql9 = "SELECT * FROM {} WHERE strategy_id=%s AND user_id=%s".format(table_baseline)
    global df_table_baseline
    df_table_baseline = query_sql(sql9, params=(sid, uid))
    print("df_table_baseline_数据库:", len(df_table_baseline))

    sql10 = "SELECT * FROM {}".format(table_index)
    global df_table_index
    print("Loading table_index...")
    df_table_index = query_sql(sql10)
    print("df_table_index_数据库:", df_table_index)

    # sql11 = f"SELECT * FROM {table_industry}"
    # 增加时间过滤
    sql11 = f"SELECT * FROM {table_industry} WHERE trade_date BETWEEN '{start_day}' AND '{stop_day}'"
    global df_table_industry
    print("Loading table_industry...")
    df_table_industry = query_sql(sql11)
    print("df_table_industry_数据库:", len(df_table_industry))

    sql12 = f"SELECT * FROM {table_labels} WHERE trade_date BETWEEN '{start_day}' AND '{stop_day}'"
    global df_table_labels
    df_table_labels = query_sql(sql12)

    # sql13 = f"SELECT * FROM {table_user_strategy_configuration}"
    # 全局配置表通常较小，或者没有 trade_date 字段，暂时保留或确认架构。
    # 假设它是配置表，SELECT * 可能没问题。如果它很大，也需要过滤。
    # 暂时不动 sql13
    sql13 = f"SELECT * FROM {table_user_strategy_configuration}"
    global df_table_user_strategy_configuration
    df_table_user_strategy_configuration = query_sql(sql13)
    # # print("df_table_industry:", len(df_table_industry))
    # df_table_industry_status_history = None
    # df_table_industry_stock = None

    sql14 = f"SELECT industry_name, trade_date, phase FROM {table_industry_status_history} WHERE trade_date BETWEEN %s AND %s"
    global df_table_industry_status_history
    df_table_industry_status_history = query_sql(sql14, params=(start_day, stop_day))
    print("df_table_industry_status_history:", len(df_table_shareholding))

    # sql15 = f"SELECT trade_date, st_code FROM {table_industry_stock}"
    # 增加时间过滤
    sql15 = f"SELECT trade_date, st_code FROM {table_industry_stock} WHERE trade_date BETWEEN '{start_day}' AND '{stop_day}'"
    global df_table_industry_stock
    if table_industry_stock == table_industry and df_table_industry is not None:
        df_table_industry_stock = df_table_industry[['trade_date', 'st_code']].copy()
    else:
        df_table_industry_stock = query_sql(sql15)
    df_table_industry_stock = deduplicate_rows(
        df_table_industry_stock,
        ['trade_date', 'st_code'],
        'df_table_industry_stock',
    )
    print("df_table_industry_stock:", len(df_table_industry_stock))


    # 读取60分钟级别数据

    # # 日期处理
    # if start_day:
    #     start_day_60m = f"{start_day[:4]}-{start_day[4:6]}-{start_day[6:8]}"
    #
    # if stop_day:
    #     stop_day_60m = f"{stop_day[:4]}-{stop_day[4:6]}-{stop_day[6:8]}"
    #
    # sql16 = f"SELECT stock_code, DATE(time) as trade_date, close,macd, pre_macd, pre_pre_macd, dif, dea, pre_dif, pre_pre_dif, pre_dea, pre_pre_dea,volume,vol_ma5,ma5,ma10 FROM {stock_60m} WHERE time BETWEEN %s AND %s AND (HOUR(time) = 14 OR HOUR(time) = 15)"
    # global df_stock_60m
    # df_stock_60m = query_sql(sql16, params=(start_day_60m, stop_day_60m))
    # print("df_table_futures_6m_数据库:", len(df_stock_60m))
    # 读取60分钟级别数据
    try:
        # 日期处理 - 支持两种格式
        if start_day:
            if '-' in start_day:
                start_day_60m = start_day
            else:
                start_day_60m = f"{start_day[:4]}-{start_day[4:6]}-{start_day[6:8]}"

        if stop_day:
            if '-' in stop_day:
                stop_day_60m = stop_day
            else:
                stop_day_60m = f"{stop_day[:4]}-{stop_day[4:6]}-{stop_day[6:8]}"
    except Exception as e:
        print(f"60分钟数据日期处理出错: {e}")
        # 默认格式处理
        start_day_60m = start_day
        stop_day_60m = stop_day

    sql16 = f"SELECT stock_code, DATE(time) as trade_date, close,macd, pre_macd, pre_pre_macd, dif, dea, pre_dif, pre_pre_dif, pre_dea, pre_pre_dea,volume,vol_ma5,ma5,ma10 FROM {stock_60m} WHERE time BETWEEN %s AND %s AND (HOUR(time) = 14 OR HOUR(time) = 15)"
    global df_stock_60m
    # df_stock_60m = query_sql(sql16, params=(start_day_60m, stop_day_60m))
    print("Loading df_stock_60m (chunked)...")
    df_stock_60m = query_custom_sql_in_chunks(sql16, start_day_60m, stop_day_60m)
    print("df_table_futures_6m_数据库:", len(df_stock_60m))

    sql17 = "SELECT * FROM {} WHERE trade_date between '{}' and '{}'".format(table_st_stock, start_day, stop_day)
    global df_table_st_stock
    print("Loading table_st_stock...")
    df_table_st_stock = query_sql(sql17)
    print("df_table_st_stock_数据库:", len(df_table_st_stock))
    # sql17 = f"SELECT st_code, trade_date, close, macd_macd, pre_macd_macd, pre_pre_macd_macd,macd_dif,last_dif FROM {stock_1d} WHERE trade_date BETWEEN %s AND %s"
    # global df_stock_1d
    # df_stock_1d = query_sql(sql17, params=(start_day_60m, stop_day_60m))
    # print("df_stock_1d_数据库:", len(df_stock_1d))

    # sql11 = "SELECT * FROM {}".format(table_deep_learning)
    # global df_deep_learning
    # df_deep_learning = query_sql(sql11)

# start_day = '20250101'
# stop_day = '20250331'
# sid = 2
# uid = 1
# Parameter = ['主板', '创业板', '中小板']  # 根据你的市场分类填写
# database(start_day, stop_day, sid, uid, Parameter)
