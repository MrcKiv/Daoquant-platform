from django.db import models


# Create your models here.

class User_Strategy_Configuration(models.Model):
    id = models.AutoField(primary_key=True)  # 显式添加自增ID字段
    userID = models.CharField(max_length=36, blank=True, null=True)  # varchar(36)
    strategyName = models.CharField(max_length=255, blank=True, null=True)  # varchar(255)
    start_date = models.TextField(blank=True, null=True)  # text
    end_date = models.TextField(blank=True, null=True)  # text
    init_fund = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)  # decimal(15,4)
    income_base = models.TextField(blank=True, null=True)  # text
    remove_st_stock = models.BooleanField(null=True, blank=True)  # tinyint(1)
    remove_suspended_stok = models.BooleanField(null=True, blank=True)  # tinyint(1)
    optionfactor = models.TextField(blank=True, null=True)  # text
    factor = models.TextField(blank=True, null=True)  # text
    bottomfactor = models.TextField(blank=True, null=True)  # text
    labels = models.TextField(blank=True, null=True)  # text
    max_hold_num = models.IntegerField(blank=True, null=True)  # int(11)

    # 订阅相关字段
    is_subscribed = models.BooleanField(null=True, blank=True, default=False)  # 是否为订阅策略
    subscription_date = models.DateTimeField(auto_now_add=True, null=True)  # 订阅时间
    source_strategy_id = models.IntegerField(blank=True, null=True)  # 原始策略ID（如果是订阅的策略）
    source_user_id = models.CharField(max_length=36, blank=True, null=True)  # varchar(36)
    # 公开相关字段
    is_public = models.BooleanField(null=True, blank=True, default=False)  # 是否为公开策略

    class Meta:
        managed = False
        db_table = '用户策略配置表'
        unique_together = ('userID', 'strategyName')  # 确保每个用户对每个策略只能订阅一次

class Strategy(models.Model):

    strategy_name = models.CharField(max_length=30)
    introduction = models.CharField(max_length=5000)
    buy_policy_list = models.CharField(max_length=1000, blank=True, null=True)
    sell_policy_list = models.CharField(max_length=1000, blank=True, null=True)
    author = models.CharField(max_length=30)
    fav_nums = models.CharField(max_length=10, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    star = models.CharField(max_length=10, blank=True, null=True)
    strategy_id = models.IntegerField()
    uid = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Strategy_Lego'

class SaveState(models.Model):
    state_id = models.CharField(max_length=10)
    state_xml = models.CharField(max_length=3000)
    state_name = models.CharField(max_length=30)
    save_time = models.DateTimeField()
    class Meta:
        managed = False
        db_table = 'Save_LegoState'

class StrategyDynamic(models.Model):
    strategy = models.ForeignKey(Strategy,on_delete=models.DO_NOTHING)
    time = models.DateField(blank=True, null=True)
    fav_nums = models.CharField(max_length=10, blank=True, null=True)
    subscription_nums = models.CharField(max_length=10, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    star = models.CharField(max_length=1, blank=True, null=True)
    star_12345 = models.CharField(max_length=10, blank=True, null=True)
    dates = models.CharField(max_length=10, blank=True, null=True)
    year_profit = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Strategy_Lego_Dynamic'

class Historical_transaction_information(models.Model):
    trade_date = models.CharField(max_length=10, blank=True, null=True)
    st_code = models.CharField(max_length=255, blank=True, null=True)
    st_name = models.CharField(max_length=255, blank=True, null=True)
    trade_type = models.CharField(max_length=5, blank=True, null=True)
    trade_price = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    number_of_transactions = models.IntegerField(blank=True, null=True)
    turnover = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    user_id = models.CharField(max_length=36, blank=True, null=True)
    strategy = models.ForeignKey(Strategy,on_delete=models.DO_NOTHING)
    strategy_name = models.CharField(max_length=30, blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'new_war_历史成交信息表'


class Current_shareholding_information(models.Model):
    trade_date = models.CharField(max_length=10, blank=True, null=True)
    st_code = models.CharField(max_length=255, blank=True, null=True)
    st_name = models.CharField(max_length=255, blank=True, null=True)
    number_of_securities = models.IntegerField(blank=True, null=True)
    saleable_quantity = models.IntegerField(blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    profit_and_loss = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    profit_and_loss_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    latest_value = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    user_id = models.CharField(max_length=36, blank=True, null=True)
    strategy = models.ForeignKey(Strategy,on_delete=models.DO_NOTHING)
    strategy_name = models.CharField(max_length=30, blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'new_war_当前持股信息表'


class Daily_statistics(models.Model):
    trade_date = models.CharField(max_length=10, blank=True, null=True)
    balance = models.FloatField(blank=True, null=True)
    available = models.FloatField(blank=True, null=True)
    reference_market_capitalization = models.FloatField(blank=True, null=True)
    assets = models.FloatField(blank=True, null=True)
    profit_and_loss = models.FloatField(blank=True, null=True)
    profit_and_loss_ratio = models.FloatField(blank=True, null=True)
    user_id = models.CharField(max_length=36, blank=True, null=True)
    strategy = models.ForeignKey(Strategy,on_delete=models.DO_NOTHING)
    strategy_name = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'new_war_每日统计表'

class Baseline_Profit_Loss(models.Model):
    trade_date = models.CharField(max_length=10, blank=True, null=True)
    assets = models.FloatField(blank=True, null=True)
    profit_and_loss = models.FloatField(blank=True, null=True)
    profit_and_loss_ratio = models.FloatField(blank=True, null=True)
    reference_market_capitalization = models.FloatField(blank=True, null=True)
    strategy_id = models.IntegerField(blank=True, null=True)
    user_id = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '大盘盈亏表'


class Baseline_index(models.Model):
    ts_code = models.CharField(max_length=255, blank=True, null=True)
    trade_date = models.CharField(max_length=10, blank=True, null=True)
    close = models.IntegerField(blank=True, null=True)
    open = models.IntegerField(blank=True, null=True)
    high = models.IntegerField(blank=True, null=True)
    low = models.IntegerField(blank=True, null=True)
    pre_close = models.IntegerField(blank=True, null=True)
    change = models.IntegerField(blank=True, null=True)
    pct_chg = models.IntegerField(blank=True, null=True)
    vol = models.IntegerField(blank=True, null=True)
    amount = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = '大盘指数'


class Stock_Basic_Info(models.Model):
    st_code = models.CharField(max_length=255, blank=True, null=True)  # 股票代码
    name = models.CharField(max_length=255, blank=True, null=True)  # 股票名称
    list_date = models.CharField(max_length=255, blank=True, null=True)  # 上市日期

    class Meta:
        managed = False
        db_table = '股票基本信息remove'


class Industry_Daily_Info(models.Model):
    st_code = models.CharField(max_length=255, blank=True, null=True)  # 股票代码
    Industry_name = models.CharField(max_length=255, blank=True, null=True)  # 行业名称

    class Meta:
        managed = False
        db_table = '仅当日行业表'

