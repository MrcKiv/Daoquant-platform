import pandas as pd
import pymysql as mdb
from sqlalchemy import create_engine
import ast

# 设置 pandas 的显示选项
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# conn = mdb.connect(host="127.0.0.1", port=3306, user='root', passwd='123456', db='stockdb', charset='utf8')
# engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/test?charset=utf8")
# cursor = conn.cursor()
import strategy.mysql_connect as sc

# today_date = pd.Timestamp.today().strftime('%Y%m%d')

def estimate_capacity(df, capacity_method='max', window=6):
    """
    估计每个行业的资金容纳量。

    参数：
      df: DataFrame，包含 'trade_date', 'Industry_code', 'trend' 三列。
      capacity_method: 'max' 或 'rolling'，'max'为用全历史期累计流入峰值，'rolling'为滚动窗口内最大累计流入。
      window: 若使用 rolling 方法，则需要指定滚动窗口长度（交易日数）。

    返回：
      capacity_df: DataFrame，索引为Industry_code，对应的资金容纳量（例如：累计流入峰值）。
    """
    df_sorted = df.sort_values(['Industry_code', 'trade_date']).copy()
    # 计算每个行业的累计流入（累计净资金变化）
    df_sorted['cum_trend'] = df_sorted.groupby('Industry_code')['trend'].cumsum()

    if capacity_method == 'max':
        capacity = df_sorted.groupby('Industry_code')['cum_trend'].max().rename('capacity')
    elif capacity_method == 'rolling':
        if window is None:
            raise ValueError("使用rolling方式时需要指定window参数")

        # 对于每个行业，计算滚动窗口内的累计流入峰值（这里用滚动最大值）
        def rolling_capacity(grp):
            grp = grp.copy()
            grp['rolling_cum'] = grp['trend'].rolling(window, min_periods=1).sum()
            return grp['rolling_cum'].max()

        capacity = df_sorted.groupby('Industry_code').apply(rolling_capacity).rename('capacity')
    else:
        raise ValueError("未知的capacity_method")

    capacity_df = capacity.reset_index()
    return capacity_df


def compute_daily_investment_pool(df, capacity_df, threshold=0.6, trend_window=3, window=4):
    """
    根据历史趋势数据和估计的资金容量，确定每日的投资行业池。

    参数：
      df: DataFrame，包含 'trade_date', 'Industry_code', 'trend'
      capacity_df: DataFrame，包含 'Industry_code' 和 'capacity'
      threshold: 流入资金与容量的比例阈值，例如0.6
      trend_window: 用于判断当前资金趋势的短期窗口天数
      window: 用于计算每个行业的累计流入时的窗口天数

    返回：
      pool_df: DataFrame，每个交易日对应的投资行业列表。
    """
    # 排序数据并合并容量数据
    df_sorted = df.sort_values(['Industry_code', 'trade_date']).copy()
    df_sorted = df_sorted.merge(capacity_df, on='Industry_code', how='left')

    # 计算每个行业的累计流入
    df_sorted['cum_trend'] = df_sorted.groupby('Industry_code')['trend'].transform(
        lambda x: x.rolling(window, min_periods=1).sum()
    )

    # 计算短期窗口内的资金流均值，用于判断当前是否处于流入趋势
    df_sorted['short_term_mean'] = df_sorted.groupby('Industry_code')['trend'] \
        .transform(lambda x: x.rolling(trend_window, min_periods=1).mean())

    # 定义一个函数，根据行业内的记录判断是否进入投资池
    def evaluate_pool(grp):
        grp = grp.copy()
        grp['include'] = False
        # 对于每一日判断：
        # 若短期均值大于0（表示当前流入趋势）且累计流入占比小于阈值，则认为该行业当日可进入投资池
        grp['inflow_ratio'] = grp['cum_trend'] / grp['capacity']

        # 条件1：短期均值大于0
        cond1 = grp['short_term_mean'] > 0

        # 条件2：连续两日的 trend 值均为正
        cond2 = (grp['trend'] > 0) & (grp['trend'].shift(1) > 0)

        # 条件3：前一日 trend 为负，当日 trend 为正，且当日 trend 大于前一日 trend 绝对值
        cond3 = (grp['trend'].shift(1) < 0) & (grp['trend'] > 0) & (grp['trend'] > grp['trend'].shift(1).abs())

        # 三个条件取或的关系
        combined_cond = cond1 | cond2 | cond3

        grp.loc[combined_cond & (grp['inflow_ratio'] < threshold), 'include'] = True
        return grp

    df_eval = df_sorted.groupby('Industry_code').apply(evaluate_pool).reset_index(drop=True)

    print(df_eval)

    # 按交易日汇总，将符合条件的行业编码列出
    pool_df = df_eval[df_eval['include']].groupby('trade_date')['Industry_code'] \
        .apply(list).reset_index().rename(columns={'Industry_code': 'investment_pool'})

    return pool_df


def process_industry_data(start_date):
    """
    处理行业数据，估计资金容量，计算每日投资行业池，并筛选满足条件的个股。
    """

    # 读取数据
    # 读取数据
    sql = f"SELECT * FROM 每日行业流向 WHERE trade_date >= {start_date}"
    # cursor.execute(sql)
    # df = pd.read_sql(sql, conn)
    df = sc.safe_read_sql(sql)

    # 估计资金容量
    capacity_df = estimate_capacity(df, capacity_method='rolling', window=6)
    print("资金容量估计：")
    print(capacity_df)
    # capacity_df.to_csv('./资金容量估计.csv', index=False)

    # 计算每日投资行业池
    pool_df = compute_daily_investment_pool(df, capacity_df, threshold=0.6, trend_window=3, window=6)
    print("\n每日投资行业池：")
    print(pool_df)
    # pool_df.to_csv('./每日投资行业池.csv', index=False)

    # 处理 NaN 并解析列表字符串
    def safe_eval(val):
        if isinstance(val, str):
            return ast.literal_eval(val)
        return val

    pool_df['investment_pool'] = pool_df['investment_pool'].fillna("[]").apply(safe_eval)

    # 使用 explode() 拆分列表
    expanded_df = pool_df.explode('investment_pool')
    Industry_code = expanded_df[['trade_date', 'investment_pool']]
    print(Industry_code)

    # 初始化一个空的 DataFrame 用于存储所有结果
    all_dfa = pd.DataFrame(columns=['trade_date', 'Industry_code', 'Industry_name', 'st_code'])

    for index, row in Industry_code.iterrows():
        trade_date = row['trade_date']
        industry_code = row['investment_pool']

        sql = f"SELECT trade_date, Industry_code, Industry_name, st_code, Main_net_amount, oversize_inflow, big_inflow FROM 行业个股流向细节 WHERE trade_date = '{trade_date}' AND Industry_code = '{industry_code}'"
        # cursor.execute(sql)
        # results = cursor.fetchall()
        results_df = sc.safe_read_sql(sql)
        results = results_df.values.tolist()

        filtered_results = [
            row for row in results
            if sum(1 for value in row[3:] if value is not None and float(value) > 0) >= 2
        ]

        data = [(row[0], row[1], row[2], row[3]) for row in filtered_results]
        dfa = pd.DataFrame(data, columns=['trade_date', 'Industry_code', 'Industry_name', 'st_code'])
        dfa['st_code'] = dfa['st_code'].apply(lambda x: x + '.SH' if x.startswith('6') else (
            x + '.BJ' if x.startswith('8') or x.startswith('4') or x.startswith('9') else x + '.SZ'))
        dfa['trade_date'] = trade_date

        all_dfa = pd.concat([all_dfa, dfa], ignore_index=True)

    # 关闭数据库连接
    # 关闭数据库连接
    # cursor.close()
    # conn.close()

    return all_dfa

# 示例用法：
# if __name__ == "__main__":
#
#
#     all_dfa = process_industry_data(start_date=20250225)
#     # 将总的 DataFrame 写入 CSV 文件
#     all_dfa.to_csv('./所有行业满足股票表.csv', index=False)