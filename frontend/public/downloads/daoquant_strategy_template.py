"""
Daoquant 自定义策略模板

使用说明：
1. 保留 `strategy_main` 作为入口函数名
2. 函数签名不要改，平台会按固定参数调用
3. 你可以先直接运行这个模板：它默认复用内置 Mark 策略
4. 想写自己的逻辑时，把 `return mark_main(...)` 换成你的实现
"""


def strategy_main(
    Init_fund,
    Investment_ratio,
    Hold_stock_num,
    Start_time,
    End_time,
    Optionfacname,
    Botfacname,
    sid,
    uid,
):
    """
    平台会按这个签名调用你的策略。

    参数说明：
    - Init_fund: 初始资金
    - Investment_ratio: 投资比例
    - Hold_stock_num: 最大持仓数
    - Start_time: 回测开始日期，格式 YYYYMMDD
    - End_time: 回测结束日期，格式 YYYYMMDD
    - Optionfacname: 策略选择配置
    - Botfacname: 因子配置
    - sid: 当前策略配置 ID
    - uid: 当前用户 ID
    """

    print("自定义策略模板已加载，当前使用 Mark策略 作为示例。")
    print(f"回测区间: {Start_time} -> {End_time}")
    print(f"策略选择配置: {Optionfacname}")
    print(f"因子配置: {Botfacname}")

    # 这是一个可直接运行的示例。
    # 如果你想完全自定义，就删掉下面这段，换成自己的回测逻辑。
    from strategy.策略.Mark import mark_main

    return mark_main(
        Init_fund,
        Investment_ratio,
        Hold_stock_num,
        Start_time,
        End_time,
        Optionfacname,
        Botfacname,
        sid,
        uid,
    )

