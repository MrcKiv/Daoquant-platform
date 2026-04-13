# -*- coding: utf-8 -*-
"""
优化版数据库操作模块
增加了更多字段支持和更好的错误处理
"""

import pandas as pd
from sqlalchemy import create_engine, text, inspect
from config import *
import strategy.mysql_connect as sc

class DatabaseManager:
    def __init__(self):
        """初始化数据库连接"""
        self.engine = create_engine(
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )

    def get_stock_data(self, start_date=None, end_date=None, limit=None):
        """
        获取股票数据（优化版）

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 限制记录数量

        Returns:
            DataFrame: 股票数据
        """
        try:
            # 首先检查表是否存在
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            print(f"数据库中的表: {tables}")

            if STOCK_DATA_TABLE not in tables:
                print(f"错误：表 '{STOCK_DATA_TABLE}' 不存在")
                return pd.DataFrame()

            # 检查字段是否存在
            columns = inspector.get_columns(STOCK_DATA_TABLE)
            column_names = [col['name'] for col in columns]
            print(f"表中的字段: {column_names}")

            # 检查特征字段
            missing_columns = []
            available_columns = []

            for col in FEATURE_COLUMNS:
                if col in column_names:
                    available_columns.append(col)
                else:
                    missing_columns.append(col)

            if missing_columns:
                print(f"警告：缺少字段 {missing_columns}")
                print(f"使用可用字段: {available_columns}")

            if not available_columns:
                print("错误：没有可用的特征字段")
                return pd.DataFrame()

            # 构建查询
            query = f"""
            SELECT st_code, trade_date, {', '.join(available_columns)}
            FROM {STOCK_DATA_TABLE}
            WHERE 1=1
            """

            if start_date:
                query += f" AND trade_date >= '{start_date}'"
            if end_date:
                query += f" AND trade_date <= '{end_date}'"

            query += " ORDER BY st_code, trade_date"

            if limit:
                query += f" LIMIT {limit}"

            print(f"执行SQL查询: {query}")

            # df = pd.read_sql(query, self.engine)
            # Use safe_read_sql
            df = sc.safe_read_sql(query)
            print(f"成功获取 {len(df)} 条股票数据")

            if not df.empty:
                print(f"数据列: {list(df.columns)}")
                print(f"数据范围: {df['trade_date'].min()} 到 {df['trade_date'].max()}")
                print(f"股票数量: {df['st_code'].nunique()}")

                # 数据质量检查
                self._check_data_quality(df)

            return df

        except Exception as e:
            print(f"获取股票数据失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _check_data_quality(self, df):
        """检查数据质量"""
        print("\n数据质量检查:")

        # 检查缺失值
        missing_counts = df[FEATURE_COLUMNS].isnull().sum()
        if missing_counts.sum() > 0:
            print(f"缺失值统计:\n{missing_counts[missing_counts > 0]}")

        # 检查异常值
        for col in FEATURE_COLUMNS:
            if col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    q1 = df[col].quantile(0.01)
                    q99 = df[col].quantile(0.99)
                    print(f"{col}: 1%-99%分位数范围 [{q1:.4f}, {q99:.4f}]")

    def get_stock_labels(self, stock_codes=None):
        """
        获取股票标签数据

        Args:
            stock_codes: 股票代码列表

        Returns:
            DataFrame: 股票标签数据
        """
        query = f"SELECT * FROM {STOCK_LABEL_TABLE}"

        if stock_codes:
            codes_str = "', '".join(stock_codes)
            query += f" WHERE st_code IN ('{codes_str}')"

        try:
            # df = pd.read_sql(query, self.engine)
            df = sc.safe_read_sql(query)
            print(f"成功获取 {len(df)} 条标签数据")
            return df
        except Exception as e:
            print(f"获取标签数据失败: {e}")
            return pd.DataFrame()

    def get_industry_tags(self, stock_codes=None):
        """
        获取行业标签数据

        Args:
            stock_codes: 股票代码列表

        Returns:
            DataFrame: 行业标签数据
        """
        query = f"SELECT * FROM {INDUSTRY_TAG_TABLE}"

        if stock_codes:
            codes_str = "', '".join(stock_codes)
            query += f" WHERE st_code IN ('{codes_str}')"

        try:
            # df = pd.read_sql(query, self.engine)
            df = sc.safe_read_sql(query)
            print(f"成功获取 {len(df)} 条行业标签数据")
            return df
        except Exception as e:
            print(f"获取行业标签数据失败: {e}")
            return pd.DataFrame()

    def test_connection(self):
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("数据库连接成功！")

                # 测试数据库名称
                db_result = conn.execute(text("SELECT DATABASE()"))
                db_name = db_result.fetchone()[0]
                print(f"当前数据库: {db_name}")

                return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            print(f"连接字符串: mysql+pymysql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
            return False

    def get_data_statistics(self):
        """获取数据统计信息"""
        try:
            # 获取所有数据
            all_data = self.get_stock_data()

            if all_data.empty:
                return {}

            stats = {
                'total_records': len(all_data),
                'stock_count': all_data['st_code'].nunique(),
                'date_range': {
                    'start': str(all_data['trade_date'].min()),
                    'end': str(all_data['trade_date'].max())
                },
                'feature_stats': {}
            }

            # 特征统计
            for col in FEATURE_COLUMNS:
                if col in all_data.columns:
                    col_data = all_data[col].dropna()
                    if len(col_data) > 0:
                        stats['feature_stats'][col] = {
                            'count': len(col_data),
                            'mean': float(col_data.mean()),
                            'std': float(col_data.std()),
                            'min': float(col_data.min()),
                            'max': float(col_data.max())
                        }

            return stats

        except Exception as e:
            print(f"获取数据统计失败: {e}")
            return {}


# 在 DatabaseManager 类中添加新方法

    def get_training_data(self, start_date=None, end_date=None, limit=None):
        """
        获取训练数据（从大表）

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制记录数

        Returns:
            DataFrame: 训练数据
        """
        try:
            # 构建查询条件
            conditions = ["1=1"]
            params = {}

            if start_date:
                conditions.append("trade_date >= %(start_date)s")
                params['start_date'] = start_date

            if end_date:
                conditions.append("trade_date <= %(end_date)s")
                params['end_date'] = end_date

            # 构建SQL查询
            query = f"""
                SELECT st_code, trade_date, close, pct_chg, vol, 
                       macd_macd, macd_dif, ema12, ema26,
                       kdj_k, kdj_d, cci, wr_wr1, close_max__20
                FROM {TRAINING_DATA_TABLE}
                WHERE {' AND '.join(conditions)}
                ORDER BY st_code, trade_date
            """

            if limit:
                query += f" LIMIT {limit}"

            print(f"执行训练数据查询: {query}")

            # 执行查询
            # df = pd.read_sql(query, self.engine, params=params)
            df = sc.safe_read_sql(query, params=params)

            if not df.empty:
                print(f"✅ 成功获取 {len(df)} 条训练数据")
                print(f"数据范围: {df['trade_date'].min()} 到 {df['trade_date'].max()}")
                print(f"股票数量: {df['st_code'].nunique()}")
            else:
                print("❌ 没有获取到训练数据")

            return df

        except Exception as e:
            print(f"❌ 获取训练数据失败: {e}")
            return pd.DataFrame()
