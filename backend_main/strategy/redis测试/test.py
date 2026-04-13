from stock_cache import (
    cache_next_n_trade_days,
    query_redis_by_date_range,
    update_latest_cache
)

# 缓存未来5个有数据的交易日
# cache_next_n_trade_days("20250226", n=51)


# 查询某个时间段的全部数据
df = query_redis_by_date_range("20250226", "20250514")

# # 更新今日数据并滑动窗口清理
# update_latest_cache("20250120")
