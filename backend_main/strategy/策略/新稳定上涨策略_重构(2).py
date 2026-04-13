import pandas as pd
import numpy as np
import multiprocessing
from multiprocessing import Process, Queue
import warnings
warnings.filterwarnings('ignore')

import strategy.mysql_connect as sc
# 数据库配置
# engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/stock?charset=utf8")

# 新增：真实数据加载函数
def load_real_data(start_date='2024-01-01', end_date='2024-12-31'):
    """
    从MySQL数据库加载真实股票数据
    """
    try:
        # 1. 加载技术指标数据
        partition_query = f"""
        SELECT 
            st_code,
            trade_date,
            open,
            high,
            low,
            close,
            pre_close,
            change,
            vol,
            cci,
            pre_cci,
            macd_macd,
            pre_macd_macd,
            rsv,
            kdj_k,
            kdj_d,
            kdj_j,
            ema12,
            ema26,
            macd_dif,
            macd_dea,
            wr_wr1,
            wr_wr2,
            boll_boll,
            boll_ub,
            boll_lb,
            week_ema_short,
            week_ema_long,
            week_macd_dif,
            lastweek_macd_dif,
            week_macd_dea,
            week_macd_macd,
            lastweek_macd_macd,
            TYP,
            ma_TYP_14,
            AVEDEV,
            last_dif,
            pre_pre_macd_macd,
            close_max__20,
            macd_max__20
        FROM partition_table
        WHERE trade_date >= '{start_date}'
        {f"AND trade_date <= '{end_date}'" if end_date else ""}
        ORDER BY trade_date, st_code
        """
        
        print("正在加载partition_table数据...")
        partition_df = sc.safe_read_sql(partition_query)
        
        # 2. 加载股票标签数据
        stocklabel_query = f"""
        SELECT 
            st_code,
            Annualized_income,
            strong_year_label,
            new_low_label,
            fall_200,
            Up_200,
            CCI_Oversold,
            WR_Oversold
        FROM 股票标签
        ORDER BY st_code
        """
        
        print("正在加载股票标签数据...")
        stocklabel_df = sc.safe_read_sql(stocklabel_query)
        
        # 3. 加载概念标签数据
        industrylabel_query = f"""
        SELECT 
            trade_date,
            industry_code,
            accumulator,
            momentum_contender,
            stability_leader,
            consistent_outflow,
            kurtosis_skew_extreme,
            spike_and_drop
        FROM advanced_industry_tags
        WHERE trade_date >= '{start_date}'
        {f"AND trade_date <= '{end_date}'" if end_date else ""}
        ORDER BY trade_date, industry_code
        """
        
        print("正在加载概念标签数据...")
        industrylabel_df = sc.safe_read_sql(industrylabel_query)
        
        # 4. 加载行业映射数据
        industry_mapping_query = """
        SELECT 
            st_code,
            industry_code
        FROM 个股行业映射
        """
        
        print("正在加载行业映射数据...")
        industry_mapping_df = sc.safe_read_sql(industry_mapping_query)
        
        print(f"数据加载完成:")
        print(f"  partition_table: {len(partition_df)} 条记录")
        print(f"  股票标签: {len(stocklabel_df)} 条记录")
        print(f"  概念标签: {len(industrylabel_df)} 条记录")
        print(f"  行业映射: {len(industry_mapping_df)} 条记录")
        
        return partition_df, stocklabel_df, industrylabel_df, industry_mapping_df
        
    except Exception as e:
        print(f"数据加载失败: {e}")
        return None, None, None, None

# 策略配置
class StrategyConfig:
    """策略配置类"""
    # 1) 数据准备阶段
    MIN_CLOSE_PRICE = 1.0  # 最低收盘价
    VOL_RANK_THRESHOLD = 0.1  # 成交量排名阈值(10%)
    
    # 2) 第一阶段：硬筛条件
    REQUIRED_POSITIVE_LABELS = ['Up_200', 'strong_year_label', 'Annualized_income']  # 必须命中其一
    NEGATIVE_FILTERS = ['new_low_label', 'fall_200']  # 必须不命中
    INDUSTRY_NEGATIVE_FILTERS = ['consistent_outflow', 'kurtosis_skew_extreme', 'spike_and_drop']  # 行业否决
    
    # 3) 第二阶段：打分模块权重
    MOMENTUM_SHORT_WEIGHT = 0.30  # 短期动量权重
    TREND_WEEKLY_WEIGHT = 0.25   # 周线趋势权重
    REVERSAL_WEIGHT = 0.10       # 反转/均值回归权重
    LIQUIDITY_WEIGHT = 0.05      # 流动性权重
    CONCEPT_WEIGHT = 0.10        # 概念/行业权重
    VOL_RISK_PENALTY_WEIGHT = 0.20  # 风险惩罚权重
    
    # 4) 组合构建
    MIN_SCORE = 60  # 最低入选分数
    TOP_K = 10      # 每日选股数量
    MAX_STOCK_WEIGHT = 0.08  # 单票上限8%
    MAX_INDUSTRY_WEIGHT = 0.35  # 行业上限35%
    
    # 5) 风控参数
    STOP_LOSS = -0.08  # 止损8%
    TAKE_PROFIT = 0.12  # 止盈12%
    MAX_TURNOVER = 0.50  # 最大换手率50%
    TRADING_COST = 0.0003  # 交易成本3bps
    CASH_BUFFER = 0.05  # 现金缓冲5%

def merge_all_tables(partition_df, stocklabel_df, industrylabel_df, industry_mapping_df):
    """
    数据准备与合并 - 阶段1
    整合所有需要的标签和数据
    """
    # 确保时间格式一致
    for df in [partition_df, stocklabel_df, industrylabel_df]:
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
    
    # 1. 基础数据合并
    merged_df = partition_df.copy()
    
    # 合并股票标签
    if stocklabel_df is not None and not stocklabel_df.empty:
        merged_df = pd.merge(
            merged_df, 
            stocklabel_df, 
            on=['st_code'], 
            how='left'
        )
    
    # 合并行业映射
    if industry_mapping_df is not None and not industry_mapping_df.empty:
        merged_df = pd.merge(
            merged_df,
            industry_mapping_df[['st_code', 'industry_code']],
            on=['st_code'],
            how='left'
        )
    
    # 合并概念标签（按行业广播）
    if industrylabel_df is not None and not industry_mapping_df is not None:
        if not industrylabel_df.empty and not industry_mapping_df.empty:
            concept_broadcast = pd.merge(
                industry_mapping_df,
                industrylabel_df,
                on=['industry_code'],
                how='left'
            )
            merged_df = pd.merge(
                merged_df,
                concept_broadcast,
                on=['st_code', 'trade_date'],
                how='left',
                suffixes=('', '_concept')
            )
    
    # 处理缺失值 - 二值标签设为0
    binary_labels = [
        'strong_year_label', 'new_low_label', 'fall_200',
        'consistent_outflow', 'kurtosis_skew_extreme', 'spike_and_drop',
        'accumulator', 'momentum_contender', 'stability_leader',
        'CCI_Oversold', 'WR_Oversold'
    ]
    
    for label in binary_labels:
        if label in merged_df.columns:
            merged_df[label] = merged_df[label].fillna(0).astype(int)
        else:
            merged_df[label] = 0
    
    # 计算成交量排名
    if 'vol' in merged_df.columns:
        merged_df['vol_rank'] = merged_df.groupby('trade_date')['vol'].rank(pct=True)
    else:
        merged_df['vol_rank'] = 1.0
    
    return merged_df

def stage1_filter(df, config=StrategyConfig):
    """
    第一阶段：硬筛 - "能不能投"
    """
    filters = []
    
    # 流动性与价格过滤
    filters.append(df['vol_rank'] >= config.VOL_RANK_THRESHOLD)
    filters.append(df['close'] >= config.MIN_CLOSE_PRICE)
    
    # 正向必须命中其一
    positive_mask = df[config.REQUIRED_POSITIVE_LABELS].sum(axis=1) > 0
    filters.append(positive_mask)
    
    # 负向必须不命中
    negative_mask = df[config.NEGATIVE_FILTERS].sum(axis=1) == 0
    filters.append(negative_mask)
    
    # 行业否决（如有行业信息）
    if 'industry_code' in df.columns:
        industry_negative_mask = df[config.INDUSTRY_NEGATIVE_FILTERS].sum(axis=1) == 0
        filters.append(industry_negative_mask)
    
    # 合并所有条件
    pass_filter = pd.Series([True] * len(df))
    for mask in filters:
        pass_filter &= mask
    
    df['pass_filter'] = pass_filter
    return df

def compute_quantile_score(series, group_keys=None, df=None):
    """
    计算分位数得分 [0,1]
    """
    if group_keys is None or df is None:
        # 全局分位数
        return series.rank(pct=True)
    else:
        # 分组分位数（行业中性化）
        try:
            # 创建包含分组键的DataFrame，保持索引一致
            temp_df = pd.DataFrame({
                'value': series.values,
                'index': series.index
            })
            
            # 添加分组键
            for key in group_keys:
                if key in df.columns:
                    temp_df[key] = df.loc[series.index, key].values
            
            # 按分组键分组计算分位数
            grouped_ranks = temp_df.groupby(group_keys)['value'].rank(pct=True)
            
            # 确保返回的Series具有正确的索引
            if isinstance(grouped_ranks, pd.Series):
                # 如果grouped_ranks已经是Series，直接返回
                return grouped_ranks
            else:
                # 如果grouped_ranks是DataFrame，需要重新索引
                result = pd.Series(grouped_ranks.values, index=series.index)
                return result
                
        except Exception as e:
            print(f"分组分位数计算失败: {e}，使用全局分位数")
            return series.rank(pct=True)

def compute_scores(df, config=StrategyConfig):
    """
    第二阶段：打分模块 - "好到什么程度"
    修改：对二值标签采用更合适的处理策略
    """
    # 准备分组键
    group_keys = ['trade_date']
    if 'industry_code' in df.columns:
        group_keys.append('industry_code')
    
    # 3.1 短期动量 momentum_short
    momentum_signals = []
    
    # MACD动量
    if all(col in df.columns for col in ['macd_dif', 'macd_dea']):
        macd_strength = (df['macd_dif'] - df['macd_dea']) / df['close']
        macd_strength.name = 'macd_strength'
        momentum_signals.append(compute_quantile_score(macd_strength, group_keys, df))
    
    # KDJ动量
    if all(col in df.columns for col in ['kdj_k', 'kdj_d']):
        kdj_momentum = (df['kdj_k'] - df['kdj_d']) / 100
        kdj_momentum.name = 'kdj_momentum'
        momentum_signals.append(compute_quantile_score(kdj_momentum, group_keys, df))
    
    # CCI动量
    if 'cci' in df.columns:
        cci_momentum = df['cci'] / 100
        cci_momentum.name = 'cci_momentum'
        momentum_signals.append(compute_quantile_score(cci_momentum, group_keys, df))
    
    # 贴近20日最高价
    if 'close_max__20' in df.columns:
        price_position = df['close'] / df['close_max__20']
        price_position.name = 'price_position'
        momentum_signals.append(compute_quantile_score(price_position, group_keys, df))
    
    if momentum_signals:
        df['momentum_short'] = np.mean(momentum_signals, axis=0)
    else:
        df['momentum_short'] = 0.5
    
    # 3.2 周线趋势确认 trend_weekly
    weekly_signals = []
    
    # 周线EMA多头
    if all(col in df.columns for col in ['week_ema_short', 'week_ema_long']):
        ema_trend = (df['week_ema_short'] - df['week_ema_long']) / df['week_ema_long']
        ema_trend.name = 'ema_trend'
        weekly_signals.append(compute_quantile_score(ema_trend, group_keys, df))
    
    # 周MACD走强
    if 'week_macd_macd' in df.columns:
        weekly_macd = df['week_macd_macd']
        weekly_macd.name = 'weekly_macd'
        weekly_signals.append(compute_quantile_score(weekly_macd, group_keys, df))
    
    if weekly_signals:
        df['trend_weekly'] = np.mean(weekly_signals, axis=0)
    else:
        df['trend_weekly'] = 0.5
    
    # 3.3 反转/均值回归 reversal - 修改：二值标签作为权重调整因子
    reversal_signals = []
    
    # 超卖信号 - 二值标签直接作为加分项，而不是分位数计算
    oversold_cols = ['CCI_Oversold', 'WR_Oversold']
    if all(col in df.columns for col in oversold_cols):
        # 二值标签：1表示超卖，0表示不超卖
        oversold_score = df[oversold_cols].sum(axis=1) / len(oversold_cols)
        reversal_signals.append(oversold_score)
    
    # 布林带位置
    if all(col in df.columns for col in ['boll_lb', 'boll_ub', 'close']):
        boll_position = (df['close'] - df['boll_lb']) / (df['boll_ub'] - df['boll_lb'])
        boll_position.name = 'boll_position'
        reversal_signals.append(1 - compute_quantile_score(boll_position, group_keys, df))  # 翻转
    
    if reversal_signals:
        df['reversal'] = np.mean(reversal_signals, axis=0)
    else:
        df['reversal'] = 0.5
    
    # 3.4 流动性 liquidity - 使用成交额计算
    print(f"开始计算流动性评分，分组键: {group_keys}")
    
    if 'vol' in df.columns and 'close' in df.columns:
        # 计算成交额 = 成交量 × 收盘价
        turnover = df['vol'] * df['close']
        print(f"成交额信息: 长度={len(turnover)}, 数据类型={turnover.dtype}")
        print(f"成交额统计: 最小值={turnover.min():.2f}, 最大值={turnover.max():.2f}, 均值={turnover.mean():.2f}")
        
        # 检查数据有效性
        null_count = turnover.isnull().sum()
        inf_count = np.isinf(turnover).sum()
        neg_count = (turnover < 0).sum()
        
        print(f"成交额质量: NaN={null_count}, 无穷大={inf_count}, 负值={neg_count}")
        
        if turnover.isnull().all():
            print("警告: 成交额全为NaN，设置liquidity为0.5")
            df['liquidity'] = 0.5
        else:
            # 处理无效值
            turnover_clean = turnover.copy()
            print(turnover_clean.notna().sum())
            turnover_clean = turnover_clean.fillna(turnover_clean.median())
            turnover_clean = turnover_clean.replace([np.inf, -np.inf], turnover_clean.median())
            turnover_clean = turnover_clean.clip(lower=0)  # 成交额不能为负
            
            print(f"清理后成交额统计: 最小值={turnover_clean.min():.2f}, 最大值={turnover_clean.max():.2f}, 均值={turnover_clean.mean():.2f}")
            
            turnover_clean.name = 'turnover'
            
            try:
                print("开始计算成交额分位数得分...")
                liquidity_score = compute_quantile_score(turnover_clean, group_keys, df)
                # 验证结果
                if liquidity_score is None:
                    print("错误: 分位数计算结果为None")
                    df['liquidity'] = 0.5
                elif liquidity_score.isnull().all():
                    print("错误: 分位数计算结果全为NaN")
                    df['liquidity'] = 0.5
                else:
                    df['liquidity'] = liquidity_score
                    print(f"流动性评分完成，有效数据: {liquidity_score.notna().sum()}/{len(liquidity_score)}")
                    print(f"流动性分数范围: {liquidity_score.min():.4f} - {liquidity_score.max():.4f}")
                    
            except Exception as e:
                print(f"流动性评分计算失败: {e}")
                print(f"错误类型: {type(e).__name__}")
                import traceback
                print(f"详细错误信息: {traceback.format_exc()}")
                df['liquidity'] = 0.5
    elif 'vol' in df.columns:
        print("警告: 只有vol列，没有close列，使用成交量计算流动性")
        vol_series = df['vol'].copy()
        print(f"vol列信息: 长度={len(vol_series)}, 数据类型={vol_series.dtype}")
        
        if vol_series.isnull().all():
            print("警告: vol列全为NaN，设置liquidity为0.5")
            df['liquidity'] = 0.5
        else:
            vol_series_clean = vol_series.copy()
            vol_series_clean = vol_series_clean.fillna(vol_series_clean.median())
            vol_series_clean = vol_series_clean.replace([np.inf, -np.inf], vol_series_clean.median())
            vol_series_clean = vol_series_clean.clip(lower=0)
            
            try:
                liquidity_score = compute_quantile_score(vol_series_clean, group_keys, df)
                if liquidity_score is None or liquidity_score.isnull().all():
                    df['liquidity'] = 0.5
                else:
                    df['liquidity'] = liquidity_score
                    print(f"成交量流动性评分完成，有效数据: {liquidity_score.notna().sum()}/{len(liquidity_score)}")
            except Exception as e:
                print(f"成交量流动性评分计算失败: {e}")
                df['liquidity'] = 0.5
    else:
        print("警告: vol列不存在，设置liquidity为0.5")
        df['liquidity'] = 0.5
    
    # 最终验证
    if 'liquidity' in df.columns:
        final_null_count = df['liquidity'].isnull().sum()
        final_valid_count = df['liquidity'].notna().sum()
        print(f"流动性评分最终结果: 有效={final_valid_count}, 缺失={final_null_count}")
        
        if final_null_count > 0:
            print("警告: 仍有流动性分数缺失，填充为0.5")
            df['liquidity'] = df['liquidity'].fillna(0.5)
    else:
        print("错误: liquidity列未创建")
        df['liquidity'] = 0.5
    
    # 3.5 概念/行业顺风 concept - 修改：二值标签组合评分
    positive_concepts = ['accumulator', 'momentum_contender', 'stability_leader']
    negative_concepts = ['consistent_outflow', 'kurtosis_skew_extreme', 'spike_and_drop']
    
    # 二值标签组合评分：正标签加分，负标签减分
    positive_count = df[positive_concepts].sum(axis=1) if all(col in df.columns for col in positive_concepts) else pd.Series(0, index=df.index)
    negative_count = df[negative_concepts].sum(axis=1) if all(col in df.columns for col in negative_concepts) else pd.Series(0, index=df.index)
    
    # 计算概念得分：正标签越多越好，负标签越少越好
    max_positive = len(positive_concepts)
    max_negative = len(negative_concepts)
    
    if max_positive > 0 and max_negative > 0:
        concept_score = (positive_count / max_positive) - (negative_count / max_negative)
    elif max_positive > 0:
        concept_score = positive_count / max_positive
    elif max_negative > 0:
        concept_score = -negative_count / max_negative
    else:
        concept_score = pd.Series(0, index=df.index)
    
    # 将得分标准化到[0,1]区间
    df['concept'] = np.clip((concept_score + 1) / 2, 0, 1)
    
    # 3.6 风险惩罚 vol_risk_penalty
    risk_signals = []
    
    # 波动率风险
    if 'pct_chg' in df.columns:
        try:
            # 使用pct_chg计算近似波动率
            rolling_vol = df.groupby('st_code')['pct_chg'].transform(lambda x: x.rolling(20, min_periods=1).std())
            rolling_vol.name = 'rolling_vol'
            # 检查数据有效性
            if rolling_vol.isnull().all():
                print("警告: 波动率计算全为NaN，跳过此风险信号")
            else:
                rolling_vol = rolling_vol.fillna(rolling_vol.median())
                vol_risk = compute_quantile_score(rolling_vol, group_keys, df)
                risk_signals.append(vol_risk)
                print(f"波动率风险评分完成，有效数据: {rolling_vol.notna().sum()}/{len(rolling_vol)}")
        except Exception as e:
            print(f"波动率风险计算失败: {e}")
    
    # ATR近似风险
    if all(col in df.columns for col in ['close', 'pct_chg']):
        try:
            atr_approx = df['close'] * df['pct_chg'].abs() / 100
            atr_approx.name = 'atr_approx'
            # 检查数据有效性
            if atr_approx.isnull().all():
                print("警告: ATR近似计算全为NaN，跳过此风险信号")
            else:
                atr_approx = atr_approx.fillna(atr_approx.median())
                risk_signals.append(compute_quantile_score(atr_approx, group_keys, df))
                print(f"ATR风险评分完成，有效数据: {atr_approx.notna().sum()}/{len(atr_approx)}")
        except Exception as e:
            print(f"ATR风险计算失败: {e}")
    
    # 靠近布林上沿风险
    if all(col in df.columns for col in ['boll_ub', 'close']):
        try:
            upper_distance = (df['boll_ub'] - df['close']) / df['close']
            upper_distance.name = 'upper_distance'
            # 检查数据有效性
            if upper_distance.isnull().all():
                print("警告: 布林上沿距离计算全为NaN，跳过此风险信号")
            else:
                upper_distance = upper_distance.fillna(upper_distance.median())
                upper_risk = 1 - compute_quantile_score(upper_distance, group_keys, df)
                risk_signals.append(upper_risk)
                print(f"布林上沿风险评分完成，有效数据: {upper_distance.notna().sum()}/{len(upper_distance)}")
        except Exception as e:
            print(f"布林上沿风险计算失败: {e}")
    
    if risk_signals:
        df['vol_risk_penalty'] = np.mean(risk_signals, axis=0)
        print(f"风险惩罚评分完成，使用 {len(risk_signals)} 个风险信号")
    else:
        print("警告: 所有风险信号计算失败，设置vol_risk_penalty为0.5")
        df['vol_risk_penalty'] = 0.5
    
    # 3.7 新增：股票标签权重调整 - 二值标签作为动态权重调整因子
    label_weight_adjustment = pd.Series(1.0, index=df.index)  # 默认权重为1.0
    
    # 强势年份标签：有标签的股票获得权重提升
    if 'strong_year_label' in df.columns:
        label_weight_adjustment += df['strong_year_label'] * 0.2  # 强势年份标签+20%权重
    
    # 突破200日线标签：有标签的股票获得权重提升
    if 'Up_200' in df.columns:
        label_weight_adjustment += df['Up_200'] * 0.15  # 突破200日线+15%权重
    
    # 年化收益标签：有标签的股票获得权重提升
    if 'Annualized_income' in df.columns:
        label_weight_adjustment += df['Annualized_income'] * 0.1  # 年化收益+10%权重
    
    # 超卖标签：有标签的股票在反转模块获得权重提升
    if 'CCI_Oversold' in df.columns or 'WR_Oversold' in df.columns:
        oversold_labels = df[['CCI_Oversold', 'WR_Oversold']].sum(axis=1) if all(col in df.columns for col in ['CCI_Oversold', 'WR_Oversold']) else pd.Series(0, index=df.index)
        # 超卖标签越多，反转权重越高
        df['reversal'] = df['reversal'] * (1 + oversold_labels * 0.1)
    
    # 3.8 聚合总分 - 应用标签权重调整
    positive_score = (
        config.MOMENTUM_SHORT_WEIGHT * df['momentum_short'] +
        config.TREND_WEEKLY_WEIGHT * df['trend_weekly'] +
        config.REVERSAL_WEIGHT * df['reversal'] +
        config.LIQUIDITY_WEIGHT * df['liquidity'] +
        config.CONCEPT_WEIGHT * df['concept']
    )
    
    risk_penalty = config.VOL_RISK_PENALTY_WEIGHT * df['vol_risk_penalty']
    
    # 应用标签权重调整
    adjusted_positive_score = positive_score * label_weight_adjustment
    
    df['stable_uptrend_score'] = 100 * (adjusted_positive_score - risk_penalty)
    df['stable_uptrend_base_score'] = 100 * adjusted_positive_score  # 不含风险惩罚的分数
    df['label_weight_adjustment'] = label_weight_adjustment  # 保存权重调整因子
    
    return df

# def build_portfolio(df, date, config=StrategyConfig):
#     """
#     阶段4：组合构建 - "选谁+各占多少"
#     """
#     # 当日数据
#     day_df = df[df['trade_date'] == date].copy()
    
#     # 选股：通过硬筛且分数≥阈值
#     eligible = day_df[
#         (day_df['pass_filter'] == True) & 
#         (day_df['score'] >= config.MIN_SCORE)
#     ]
    
#     if len(eligible) == 0:
#         return pd.DataFrame()
    
#     # 取Top-K
#     top_stocks = eligible.nlargest(config.TOP_K, 'score')
    
#     # 计算权重
#     weights = []
    
#     # 按分数加权
#     total_score = top_stocks['score'].sum()
#     if total_score > 0:
#         initial_weights = top_stocks['score'] / total_score
#     else:
#         initial_weights = pd.Series([1.0/len(top_stocks)] * len(top_stocks))
    
#     # 行业权重限制
#     if 'industry_code' in top_stocks.columns:
#         # 按行业分组
#         industry_groups = top_stocks.groupby('industry_code')
        
#         # 调整超限行业权重
#         adjusted_weights = initial_weights.copy()
        
#         for industry, group in industry_groups:
#             industry_weight = initial_weights[group.index].sum()
#             if industry_weight > config.MAX_INDUSTRY_WEIGHT:
#                 # 压缩行业权重
#                 scale_factor = config.MAX_INDUSTRY_WEIGHT / industry_weight
#                 adjusted_weights[group.index] *= scale_factor
        
#         # 重新归一化
#         if adjusted_weights.sum() > 0:
#             adjusted_weights = adjusted_weights / adjusted_weights.sum()
        
#         weights = adjusted_weights.values
#     else:
#         weights = initial_weights.values
    
#     # 单票上限限制
#     weights = np.minimum(weights, config.MAX_STOCK_WEIGHT)
#     weights = weights / weights.sum()  # 最终归一化
    
#     # 构建结果
#     portfolio = pd.DataFrame({
#         'trade_date': date,
#         'st_code': top_stocks['st_code'].values,
#         'score': top_stocks['score'].values,
#         'weight': weights
#     })
    
#     return portfolio

def run_strategy_pipeline(partition_df, stocklabel_df, industrylabel_df, 
                         industry_mapping_df, start_date, end_date, 
                         config=StrategyConfig):
    """
    完整策略流水线
    """
    print("开始策略执行...")
    
    # 1) 数据准备
    print("1. 数据准备与合并...")
    merged_data = merge_all_tables(partition_df, stocklabel_df, industrylabel_df, 
                                  industry_mapping_df)
    
    # 2) 时间过滤
    if start_date:
        merged_data = merged_data[merged_data['trade_date'] >= pd.to_datetime(start_date)]
    if end_date:
        merged_data = merged_data[merged_data['trade_date'] <= pd.to_datetime(end_date)]
    
    # 3) 阶段1：硬筛
    print("2. 执行硬筛...")
    filtered_data = stage1_filter(merged_data, config)
    
    # 4) 阶段2：打分
    print("3. 计算分数...")
    scored_data = compute_scores(filtered_data, config)

        # 保存打分结果到CSV文件
    print("保存打分结果到CSV文件...")
    score_columns = ['trade_date', 'st_code', 'pass_filter', 'stable_uptrend_score', 'stable_uptrend_base_score', 
                     'momentum_short', 'trend_weekly', 'reversal', 'liquidity', 
                     'concept', 'vol_risk_penalty', 'label_weight_adjustment']
    
    # 筛选出存在的列
    existing_score_columns = [col for col in score_columns if col in scored_data.columns]
    score_results = scored_data[existing_score_columns].copy()
    score_results = score_results[score_results['pass_filter'] == True]

    # 按日期和分数排序（日期升序，分数降序）
    score_results = score_results.sort_values(['trade_date', 'stable_uptrend_score'], ascending=[True, False])
    
    # 保存到CSV
    score_results.to_csv('新稳定上涨策略_打分结果.csv', index=False, encoding='utf-8-sig')
    print(f"打分结果已保存到: 新稳定上涨策略_打分结果.csv，共 {len(score_results)} 条记录")
    return score_results
    
    # 5) 阶段4：组合构建
    # print("4. 构建组合...")
    # all_portfolios = []
    
    # for date in scored_data['trade_date'].unique():
    #     portfolio = build_portfolio(scored_data, date, config)
    #     if not portfolio.empty:
    #         all_portfolios.append(portfolio)
    
    # if all_portfolios:
    #     final_portfolio = pd.concat(all_portfolios, ignore_index=True)
    #     print(f"策略完成！共生成 {len(final_portfolio)} 条组合记录")
    #     return final_portfolio
    # else:
    #     print("未生成任何组合记录")
    #     return pd.DataFrame()

if __name__ == "__main__":
    # 使用真实数据运行策略
    print("=== 新稳定上涨策略 - 真实数据运行 ===")
    
    # 加载真实数据
    partition_df, stocklabel_df, industrylabel_df, industry_mapping_df = load_real_data(
        start_date='2025-04-23', 
        end_date='2025-08-01'
    )
    
    if partition_df is not None:
        # 运行策略
        score_results = run_strategy_pipeline(
            partition_df=partition_df,
            stocklabel_df=stocklabel_df,
            industrylabel_df=industrylabel_df,
            industry_mapping_df=industry_mapping_df,
            start_date='2025-04-23',
            end_date='2025-8-01'
        )
        
        # if not portfolio.empty:
        #     print(f"\n策略运行完成！")
        #     print(f"总记录数: {len(portfolio)}")
        #     print(f"覆盖日期: {portfolio['trade_date'].nunique()} 天")
        #     print(f"覆盖股票: {portfolio['st_code'].nunique()} 只")
            
        #     # 保存结果
        #     portfolio.to_csv('新稳定上涨策略结果.csv', index=False, encoding='utf-8-sig')
        #     print("结果已保存到: 新稳定上涨策略结果.csv")
        # else:
        #     print("策略未产生有效结果")
    else:
        print("数据加载失败，请检查数据库连接")