from django.db import models


class StockDailyData(models.Model):
    """股票日线行情数据 - 对应partition_table表"""
    st_code = models.CharField(max_length=20, verbose_name='股票代码')
    trade_date = models.CharField(max_length=10, verbose_name='交易日期')
    open = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='开盘价')
    high = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='最高价')
    low = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='最低价')
    close = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='收盘价')
    vol = models.BigIntegerField(verbose_name='成交量')
    pre_close = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='前收盘价')
    pct_chg = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='涨跌幅')
    
    # 技术指标
    rsv = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='RSV')
    kdj_k = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='KDJ_K')
    kdj_d = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='KDJ_D')
    kdj_j = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='KDJ_J')
    ema26 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='EMA26')
    ema12 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='EMA12')
    macd_dif = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='MACD_DIF')
    macd_dea = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='MACD_DEA')
    macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='MACD_MACD')
    wr_wr1 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='WR1')
    wr_wr2 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='WR2')
    boll_boll = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='BOLL')
    boll_ub = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='BOLL上轨')
    boll_lb = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='BOLL下轨')
    cci = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='CCI')
    
    # 周线指标
    week_ema_short = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='周线短期EMA')
    week_ema_long = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='周线长期EMA')
    week_macd_dif = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='周线MACD_DIF')
    week_macd_dea = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='周线MACD_DEA')
    week_macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='周线MACD')
    
    # 其他指标
    lastweek_macd_dif = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='上周MACD_DIF')
    lastlastweek_macd_dif = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='上上周MACD_DIF')
    lastweek_macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='上周MACD')
    lastlastweek_macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='上上周MACD')
    
    # 移动平均线和其他指标
    TYP = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='TYP')
    ma_TYP_14 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='14日移动平均')
    AVEDEV = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='AVEDEV')
    last_dif = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='last_dif')
    pre_macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='前MACD')
    pre_pre_macd_macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='前前MACD')
    pre_cci = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='前CCI')
    close_max_20 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='20日最高价')
    macd_max_20 = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='20日MACD最大值')
    
    class Meta:
        managed = False
        db_table = 'partition_table'
        verbose_name = '股票日线数据'
        verbose_name_plural = '股票日线数据'


class StockBasicInfo(models.Model):
    """股票基本信息 - 对应股票基本信息remove表"""
    st_code = models.CharField(max_length=20, primary_key=True, verbose_name='股票代码')
    symbol = models.CharField(max_length=20, null=True, blank=True, verbose_name='股票代码(不含后缀)')
    name = models.CharField(max_length=50, verbose_name='股票名称')
    area = models.CharField(max_length=50, null=True, blank=True, verbose_name='地区')
    industry = models.CharField(max_length=100, null=True, blank=True, verbose_name='行业')
    fullname = models.CharField(max_length=100, null=True, blank=True, verbose_name='股票全称')
    enname = models.CharField(max_length=200, null=True, blank=True, verbose_name='英文名称')
    market = models.CharField(max_length=20, null=True, blank=True, verbose_name='市场类型')
    list_status = models.CharField(max_length=10, null=True, blank=True, verbose_name='上市状态')
    list_date = models.CharField(max_length=10, null=True, blank=True, verbose_name='上市日期')
    delist_date = models.CharField(max_length=10, null=True, blank=True, verbose_name='退市日期')
    
    class Meta:
        managed = False
        db_table = '股票基本信息remove'
        verbose_name = '股票基本信息'
        verbose_name_plural = '股票基本信息'


class StockDiagnosisResult(models.Model):
    """股票诊断结果 - 这是一个新表，用于存储诊断结果"""
    st_code = models.CharField(max_length=20, verbose_name='股票代码')
    diagnosis_date = models.DateField(auto_now_add=True, verbose_name='诊断日期')
    
    # 技术面诊断
    technical_score = models.IntegerField(verbose_name='技术面评分', help_text='0-100分')
    technical_analysis = models.TextField(verbose_name='技术面分析')
    
    # 基本面诊断
    fundamental_score = models.IntegerField(verbose_name='基本面评分', help_text='0-100分')
    fundamental_analysis = models.TextField(verbose_name='基本面分析')
    
    # 综合诊断
    overall_score = models.IntegerField(verbose_name='综合评分', help_text='0-100分')
    overall_analysis = models.TextField(verbose_name='综合分析')
    recommendation = models.CharField(max_length=20, verbose_name='投资建议', 
                                   choices=[('buy', '买入'), ('hold', '持有'), ('sell', '卖出')])
    
    # 风险提示
    risk_level = models.CharField(max_length=20, verbose_name='风险等级',
                                choices=[('low', '低风险'), ('medium', '中等风险'), ('high', '高风险')])
    risk_factors = models.TextField(verbose_name='风险因素')
    
    class Meta:
        managed = True  # 这个表由Django管理
        db_table = 'stock_diagnosis_result'
        verbose_name = '股票诊断结果'
        verbose_name_plural = '股票诊断结果'
