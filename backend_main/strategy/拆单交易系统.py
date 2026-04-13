import pandas as pd
import time
import random
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import create_engine
import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockDataFetcher:
    def __init__(self):
        self.primary_source_available = True
        self.last_check_time = 0
        self.check_interval = 300  # 5分钟内不重复检查主数据源状态

    def gupiaopankou_dfcf(self, daima):
        """ 从东方财富网获取股票盘口实时数据（增强版）
        :param daima: 股票代码
        :return: 盘口数据
        """
        try:
            if daima[:2] == "sh":
                lsbl = '1.' + daima[2:]
            else:
                lsbl = '0.' + daima[2:]
            wangzhi = ('http://push2.eastmoney.com/api/qt/stock/get?&fltt=2&invt=2&fields='
                       'f120,f121,f122,f174,f175,f59,f163,f43,f57,f58,f169,f170,f46,f44,f51,f168,'
                       'f47,f164,f116,f60,f45,f52,f50,f48,f167,f117,f71,f161,f49,f530,f135,f136,'
                       'f137,f138,f139,f141,f142,f144,f145,f147,f148,f140,f143,f146,f149,f55,f62,'
                       'f162,f92,f173,f104,f105,f84,f85,f183,f184,f185,f186,f187,f188,f189,f190,'
                       'f191,f192,f107,f111,f86,f177,f78,f110,f262,f263,f264,f267,f268,f255,f256,'
                       'f257,f258,f127,f199,f128,f198,f259,f260,f261,f171,f277,f278,f279,f288,f152,'
                       'f250,f251,f252,f253,f254,f269,f270,f271,f272,f273,f274,f275,f276,f265,f266,'
                       'f289,f290,f286,f285,f292,f293,f294,f295&secid=' + lsbl + '&=' + str(int(time.time() * 1000)))
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://quote.eastmoney.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            resp = requests.get(wangzhi, timeout=10, headers=headers)
            if resp.status_code != 200:
                logger.error(f"HTTP请求失败，状态码: {resp.status_code}")
                return None
            if not resp.text or len(resp.text.strip()) == 0:
                logger.error("服务器返回空响应")
                return None
            try:
                json_data = resp.json()
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 响应内容: {resp.text[:200]}")
                return None
            if 'data' not in json_data or not json_data['data']:
                logger.error(f"返回数据结构异常或数据为空: {list(json_data.keys()) if json_data else '无数据'}")
                return None
            data = json_data['data']
            pankou = {
                '代码': data.get('f57', ''),
                '名称': data.get('f58', ''),
                '开盘': data.get('f46', 0),
                '最高': data.get('f44', 0),
                '最低': data.get('f45', 0),
                '最新': data.get('f43', 0),
                '金额': data.get('f48', 0),
                '卖1价': data.get('f31', 0), '卖1量': data.get('f32', 0) * 100,
                '卖2价': data.get('f33', 0), '卖2量': data.get('f34', 0) * 100,
                '卖3价': data.get('f35', 0), '卖3量': data.get('f36', 0) * 100,
                '卖4价': data.get('f37', 0), '卖4量': data.get('f38', 0) * 100,
                '卖5价': data.get('f39', 0), '卖5量': data.get('f40', 0) * 100,
                '买1价': data.get('f19', 0), '买1量': data.get('f20', 0) * 100,
                '买2价': data.get('f17', 0), '买2量': data.get('f18', 0) * 100,
                '买3价': data.get('f15', 0), '买3量': data.get('f16', 0) * 100,
                '买4价': data.get('f13', 0), '买4量': data.get('f14', 0) * 100,
                '买5价': data.get('f11', 0), '买5量': data.get('f12', 0) * 100
            }
            logger.info(f"成功获取股票 {pankou['代码']} 数据")
            return pankou
        except requests.Timeout:
            logger.error("请求超时")
            return None
        except requests.RequestException as e:
            logger.error(f"网络请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return None

    def get_stock_data_backup_tencent(self, stock_code):
        """ 备用数据源：腾讯证券
        :param stock_code: 股票代码
        :return: 盘口数据
        """
        try:
            url = f"http://qt.gtimg.cn/q={stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200 and resp.text:
                logger.info("使用腾讯证券备用数据源")
                # 解析腾讯返回的数据
                return self.parse_tencent_data(resp.text)
            return None
        except Exception as e:
            logger.error(f"腾讯证券数据源获取失败: {e}")
            return None

    def parse_tencent_data(self, raw_data):
        """ 解析腾讯证券返回的数据
        :param raw_data: 原始数据字符串
        :return: 解析后的盘口数据
        """
        try:
            # 解析类似 v_sz000001="51~平安银行~000001~11.80~11.59~11.58~..." 的数据
            if raw_data.startswith('v'):
                content = raw_data.split('=')[1].strip('"')
                items = content.split('~')
                if len(items) >= 32:
                    pankou = {
                        '代码': items[2],
                        '名称': items[1],
                        '最新': float(items[3]) if items[3] else 0,
                        '开盘': float(items[5]) if items[5] else 0,
                        '前收盘': float(items[4]) if items[4] else 0,
                        '最高': float(items[33]) if len(items) > 33 and items[33] else 0,
                        '最低': float(items[34]) if len(items) > 34 and items[34] else 0,
                        '买1价': float(items[9]) if items[9] else 0,
                        '买1量': int(items[10]) * 100 if items[10] else 0,  # 转换为股数
                        '买2价': float(items[11]) if items[11] else 0,
                        '买2量': int(items[12]) * 100 if items[12] else 0,  # 转换为股数
                        '买3价': float(items[13]) if items[13] else 0,
                        '买3量': int(items[14]) * 100 if items[14] else 0,  # 转换为股数
                        '买4价': float(items[15]) if items[15] else 0,
                        '买4量': int(items[16]) * 100 if items[16] else 0,  # 转换为股数
                        '买5价': float(items[17]) if items[17] else 0,
                        '买5量': int(items[18]) * 100 if items[18] else 0,  # 转换为股数
                        '卖1价': float(items[19]) if items[19] else 0,
                        '卖1量': int(items[20]) * 100 if items[20] else 0,  # 转换为股数
                        '卖2价': float(items[21]) if items[21] else 0,
                        '卖2量': int(items[22]) * 100 if items[22] else 0,  # 转换为股数
                        '卖3价': float(items[23]) if items[23] else 0,
                        '卖3量': int(items[24]) * 100 if items[24] else 0,  # 转换为股数
                        '卖4价': float(items[25]) if items[25] else 0,
                        '卖4量': int(items[26]) * 100 if items[26] else 0,  # 转换为股数
                        '卖5价': float(items[27]) if items[27] else 0,
                        '卖5量': int(items[28]) * 100 if items[28] else 0,  # 转换为股数
                    }
                    return pankou
            return {"source": "tencent", "raw_data": raw_data[:200]}
        except Exception as e:
            logger.error(f"解析腾讯数据失败: {e}")
            return {"source": "tencent", "raw_data": raw_data[:200]}

    def get_stock_data_backup_sina(self, stock_code):
        """ 备用数据源：新浪财经
        :param stock_code: 股票代码
        :return: 盘口数据
        """
        try:
            # 转换股票代码格式以适应新浪财经
            if stock_code.startswith('sh'):
                sina_code = 'sh' + stock_code[2:]
            elif stock_code.startswith('sz'):
                sina_code = 'sz' + stock_code[2:]
            else:
                sina_code = stock_code

            url = f"http://hq.sinajs.cn/list={sina_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200 and resp.text:
                logger.info("使用新浪财经备用数据源")
                return self.parse_sina_data(resp.text)
            return None
        except Exception as e:
            logger.error(f"新浪财经数据源获取失败: {e}")
            return None

    def parse_sina_data(self, raw_data):
        """ 解析新浪财经返回的数据
        :param raw_data: 原始数据字符串
        :return: 解析后的盘口数据
        """
        try:
            # 解析类似 var hq_str_sh601009="平安银行,11.80,11.59,11.58,..."; 的数据
            if raw_data.startswith('var'):
                content = raw_data.split('"')[1]
                items = content.split(',')
                if len(items) >= 32:
                    pankou = {
                        '代码': items[0] if len(items) > 0 else '',
                        '名称': items[0] if len(items) > 0 else '',
                        '最新': float(items[3]) if len(items) > 3 and items[3] else 0,
                        '开盘': float(items[1]) if len(items) > 1 and items[1] else 0,
                        '前收盘': float(items[2]) if len(items) > 2 and items[2] else 0,
                        '最高': float(items[4]) if len(items) > 4 and items[4] else 0,
                        '最低': float(items[5]) if len(items) > 5 and items[5] else 0,
                        '买1价': float(items[6]) if len(items) > 6 and items[6] else 0,
                        '买1量': int(items[7]) if len(items) > 7 and items[7] else 0,
                        '买2价': float(items[8]) if len(items) > 8 and items[8] else 0,
                        '买2量': int(items[9]) if len(items) > 9 and items[9] else 0,
                        '买3价': float(items[10]) if len(items) > 10 and items[10] else 0,
                        '买3量': int(items[11]) if len(items) > 11 and items[11] else 0,
                        '买4价': float(items[12]) if len(items) > 12 and items[12] else 0,
                        '买4量': int(items[13]) if len(items) > 13 and items[13] else 0,
                        '买5价': float(items[14]) if len(items) > 14 and items[14] else 0,
                        '买5量': int(items[15]) if len(items) > 15 and items[15] else 0,
                        '卖1价': float(items[16]) if len(items) > 16 and items[16] else 0,
                        '卖1量': int(items[17]) if len(items) > 17 and items[17] else 0,
                        '卖2价': float(items[18]) if len(items) > 18 and items[18] else 0,
                        '卖2量': int(items[19]) if len(items) > 19 and items[19] else 0,
                        '卖3价': float(items[20]) if len(items) > 20 and items[20] else 0,
                        '卖3量': int(items[21]) if len(items) > 21 and items[21] else 0,
                        '卖4价': float(items[22]) if len(items) > 22 and items[22] else 0,
                        '卖4量': int(items[23]) if len(items) > 23 and items[23] else 0,
                        '卖5价': float(items[24]) if len(items) > 24 and items[24] else 0,
                        '卖5量': int(items[25]) if len(items) > 25 and items[25] else 0,
                    }
                    return pankou
            return {"source": "sina", "raw_data": raw_data[:200]}
        except Exception as e:
            logger.error(f"解析新浪财经数据失败: {e}")
            return {"source": "sina", "raw_data": raw_data[:200]}

    def get_stock_data_backup_tonghuashun(self, stock_code):
        """ 备用数据源：同花顺
        :param stock_code: 股票代码
        :return: 盘口数据
        """
        try:
            # 转换股票代码格式以适应同花顺
            if stock_code.startswith('sh'):
                ths_code = stock_code[2:] + 'SH'
            elif stock_code.startswith('sz'):
                ths_code = stock_code[2:] + 'SZ'
            else:
                ths_code = stock_code

            url = f"http://d.10jqka.com.cn/v2/realhead/hs_{ths_code}/last.js"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://stock.10jqka.com.cn/'
            }
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200 and resp.text:
                logger.info("使用同花顺备用数据源")
                return self.parse_tonghuashun_data(resp.text)
            return None
        except Exception as e:
            logger.error(f"同花顺数据源获取失败: {e}")
            return None

    def parse_tonghuashun_data(self, raw_data):
        """ 解析同花顺返回的数据
        :param raw_data: 原始数据字符串
        :return: 解析后的盘口数据
        """
        try:
            # 解析同花顺返回的JSON数据
            if raw_data.startswith('quotebridge') and '(' in raw_data and ')' in raw_data:
                json_str = raw_data[raw_data.find('(') + 1:raw_data.rfind(')')]
                data = json.loads(json_str)
                snapshot = data.get('snapshot', {})

                if snapshot:
                    pankou = {
                        '代码': snapshot.get('code', ''),
                        '名称': snapshot.get('name', ''),
                        '最新': float(snapshot.get('lastPrice', 0)),
                        '开盘': float(snapshot.get('open', 0)),
                        '前收盘': float(snapshot.get('preClose', 0)),
                        '最高': float(snapshot.get('high', 0)),
                        '最低': float(snapshot.get('low', 0)),
                        '买1价': float(snapshot.get('bid1', 0)),
                        '买1量': int(snapshot.get('bidSize1', 0)),
                        '买2价': float(snapshot.get('bid2', 0)),
                        '买2量': int(snapshot.get('bidSize2', 0)),
                        '买3价': float(snapshot.get('bid3', 0)),
                        '买3量': int(snapshot.get('bidSize3', 0)),
                        '买4价': float(snapshot.get('bid4', 0)),
                        '买4量': int(snapshot.get('bidSize4', 0)),
                        '买5价': float(snapshot.get('bid5', 0)),
                        '买5量': int(snapshot.get('bidSize5', 0)),
                        '卖1价': float(snapshot.get('ask1', 0)),
                        '卖1量': int(snapshot.get('askSize1', 0)),
                        '卖2价': float(snapshot.get('ask2', 0)),
                        '卖2量': int(snapshot.get('askSize2', 0)),
                        '卖3价': float(snapshot.get('ask3', 0)),
                        '卖3量': int(snapshot.get('askSize3', 0)),
                        '卖4价': float(snapshot.get('ask4', 0)),
                        '卖4量': int(snapshot.get('askSize4', 0)),
                        '卖5价': float(snapshot.get('ask5', 0)),
                        '卖5量': int(snapshot.get('askSize5', 0)),
                    }
                    return pankou
            return {"source": "tonghuashun", "raw_data": raw_data[:200]}
        except Exception as e:
            logger.error(f"解析同花顺数据失败: {e}")
            return {"source": "tonghuashun", "raw_data": raw_data[:200]}

    def should_try_primary_source(self):
        """ 判断是否应该尝试主数据源
        :return: 是否应该尝试主数据源
        """
        current_time = time.time()
        # 如果主数据源可用，或者距离上次检查已经超过指定间隔，则尝试主数据源
        if self.primary_source_available or (current_time - self.last_check_time > self.check_interval):
            self.last_check_time = current_time
            return True
        return False

    def update_primary_source_status(self, success):
        """ 更新主数据源状态
        :param success: 是否成功
        """
        self.primary_source_available = success
        if success:
            logger.info("主数据源恢复正常")
        else:
            logger.warning("主数据源标记为不可用")

    def robust_gupiaopankou_get(self, stock_code, max_retries=3):
        """ 健壮的股票数据获取函数，支持重试和备用数据源，并记忆状态
        :param stock_code: 股票代码
        :param max_retries: 最大重试次数
        :return: 盘口数据
        """
        # 如果主数据源可用或到了检查时间，尝试主数据源
        if self.should_try_primary_source():
            for attempt in range(max_retries):
                data = self.gupiaopankou_dfcf(stock_code)
                if data:
                    self.update_primary_source_status(True)
                    return data
                logger.warning(f"主数据源第{attempt + 1}次尝试失败，等待重试...")
                # time.sleep(2)
            # 主数据源尝试失败，更新状态
            self.update_primary_source_status(False)
            logger.warning("主数据源连续失败，尝试备用数据源...")

        # 按优先级依次尝试备用数据源
        backup_sources = [
            ("腾讯证券", self.get_stock_data_backup_tencent),
            ("新浪财经", self.get_stock_data_backup_sina),
            ("同花顺", self.get_stock_data_backup_tonghuashun)
        ]

        for source_name, source_func in backup_sources:
            try:
                backup_data = source_func(stock_code)
                if backup_data and 'source' not in backup_data:
                    logger.info(f"成功从{source_name}获取数据")
                    return backup_data
                elif backup_data:
                    logger.warning(f"{source_name}返回数据异常")
            except Exception as e:
                logger.error(f"尝试{source_name}数据源时出错: {e}")

            # 短暂等待后尝试下一个数据源
            time.sleep(1)

        logger.error("所有数据源均获取失败")
        return None


# 创建全局实例
fetcher = StockDataFetcher()


def calculate_trade_quantity(row):
    """
    计算需要交易的数量
    :param row: DataFrame行数据
    :return: 需要交易的数量（手数）
    """
    if pd.notna(row['number_of_transactions']) and row['number_of_transactions'] > 0:
        return int(row['number_of_transactions'] / 100)
    elif pd.notna(row['turnover']) and pd.notna(row['trade_price']) and row['trade_price'] > 0:
        # 根据成交额和价格反算数量（假设每手100股）
        return int(row['turnover'] / row['trade_price'] / 100)
    else:
        return 0


# def split_order_strategy(row, bid_ask_data):
#     """
#     拆单策略实现 - 修改版本，确保订单完全成交
#     :param row: 原始交易数据行
#     :param bid_ask_data: 实时盘口数据
#     :return: 拆单计划
#     """
#     trade_type = row['trade_type']
#     target_quantity = calculate_trade_quantity(row)
#
#     if target_quantity <= 0:
#         return []
#
#     # 根据交易类型选择对应的盘口数据
#     if trade_type == '卖出':
#         # 卖出时关注买盘数据
#         price_levels = [
#             (bid_ask_data['买1价'], bid_ask_data['买1量']),
#             (bid_ask_data['买2价'], bid_ask_data['买2量']),
#             (bid_ask_data['买3价'], bid_ask_data['买3量']),
#             (bid_ask_data['买4价'], bid_ask_data['买4量']),
#             (bid_ask_data['买5价'], bid_ask_data['买5量'])
#         ]
#     else:  # 买入
#         # 买入时关注卖盘数据
#         price_levels = [
#             (bid_ask_data['卖1价'], bid_ask_data['卖1量']),
#             (bid_ask_data['卖2价'], bid_ask_data['卖2量']),
#             (bid_ask_data['卖3价'], bid_ask_data['卖3量']),
#             (bid_ask_data['卖4价'], bid_ask_data['卖4量']),
#             (bid_ask_data['卖5价'], bid_ask_data['卖5量'])
#         ]
#
#     # 过滤掉无效数据
#     valid_levels = [(price, vol) for price, vol in price_levels
#                     if pd.notna(price) and price != '-' and price > 0
#                     and pd.notna(vol) and vol != '-' and vol > 0]
#
#     if not valid_levels:
#         return []
#
#     order_plan = []
#     remaining_quantity = target_quantity
#
#     # 第一阶段：按价格优先级进行常规拆单
#     for price, available_vol in valid_levels:
#         if remaining_quantity <= 0:
#             break
#
#         # 计算在该价格档位最多能成交的数量
#         # 为了避免冲击市场，只取该档位可用量的50%-70%
#         max_take_ratio = random.uniform(0.5, 0.7)
#         max_take_volume = int(available_vol * max_take_ratio)
#
#         # 确定实际成交数量
#         trade_volume = min(remaining_quantity, max_take_volume)
#
#         if trade_volume > 0:
#             order_plan.append({
#                 'price': price,
#                 'volume': trade_volume * 100,
#                 'amount': price * trade_volume* 100  # 金额 = 价格 * 手数 * 100(每手股数)
#             })
#             remaining_quantity -= trade_volume
#
#     # 第二阶段：如果还有剩余未成交的数量，市价全部吃掉
#     if remaining_quantity > 0:
#         # 使用最优价格吃掉剩余订单
#         if trade_type == '卖出':
#             # 卖出使用买盘价格
#             market_price = bid_ask_data.get('买1价', valid_levels[0][0])
#             # 可以考虑依次使用买1到买5的价格来吃掉剩余订单
#             remaining_levels = [
#                 (bid_ask_data.get('买1价', 0), bid_ask_data.get('买1量', 0)),
#                 (bid_ask_data.get('买2价', 0), bid_ask_data.get('买2量', 0)),
#                 (bid_ask_data.get('买3价', 0), bid_ask_data.get('买3量', 0)),
#                 (bid_ask_data.get('买4价', 0), bid_ask_data.get('买4量', 0)),
#                 (bid_ask_data.get('买5价', 0), bid_ask_data.get('买5量', 0))
#             ]
#         else:
#             # 买入使用卖盘价格
#             market_price = bid_ask_data.get('卖1价', valid_levels[0][0])
#             # 可以考虑依次使用卖1到卖5的价格来吃掉剩余订单
#             remaining_levels = [
#                 (bid_ask_data.get('卖1价', 0), bid_ask_data.get('卖1量', 0)),
#                 (bid_ask_data.get('卖2价', 0), bid_ask_data.get('卖2量', 0)),
#                 (bid_ask_data.get('卖3价', 0), bid_ask_data.get('卖3量', 0)),
#                 (bid_ask_data.get('卖4价', 0), bid_ask_data.get('卖4量', 0)),
#                 (bid_ask_data.get('卖5价', 0), bid_ask_data.get('卖5量', 0))
#             ]
#
#         # 过滤有效档位
#         valid_remaining_levels = [(price, vol) for price, vol in remaining_levels
#                                   if pd.notna(price) and price != '-' and price > 0
#                                   and pd.notna(vol) and vol != '-' and vol > 0]
#
#         # 如果有有效档位，逐档吃掉剩余订单
#         if valid_remaining_levels:
#             for price, available_vol in valid_remaining_levels:
#                 if remaining_quantity <= 0:
#                     break
#
#                 # 确定在该档位实际成交数量（可以全部吃掉）
#                 trade_volume = min(remaining_quantity, available_vol)
#
#                 if trade_volume > 0:
#                     order_plan.append({
#                         'price': price,
#                         'volume': trade_volume * 100,
#                         'amount': price * trade_volume* 100
#                     })
#                     remaining_quantity -= trade_volume
#         else:
#             # 如果没有有效档位，则按最优价格挂单
#             order_plan.append({
#                 'price': market_price,
#                 'volume': remaining_quantity * 100,
#                 'amount': market_price * remaining_quantity* 100
#             })
#
#     return order_plan
def split_order_strategy(row, bid_ask_data):
    """
    拆单策略实现 - 修改版本，确保订单完全成交
    新的拆单逻辑：
    1. 如果目标档位的量足够，就全部买入/卖出
    2. 如果目标档位的量不足，买入该档位的80%
    3. 剩余部分继续在下一档位按同样规则处理
    4. 最后剩余部分市价成交
    :param row: 原始交易数据行
    :param bid_ask_data: 实时盘口数据
    :return: 拆单计划
    """
    trade_type = row['trade_type']
    target_quantity = calculate_trade_quantity(row)

    if target_quantity <= 0:
        return []

    # 根据交易类型选择对应的盘口数据
    if trade_type == '卖出':
        # 卖出时关注买盘数据
        price_levels = [
            (bid_ask_data['买1价'], bid_ask_data['买1量']),
            (bid_ask_data['买2价'], bid_ask_data['买2量']),
            (bid_ask_data['买3价'], bid_ask_data['买3量']),
            (bid_ask_data['买4价'], bid_ask_data['买4量']),
            (bid_ask_data['买5价'], bid_ask_data['买5量'])
        ]
    else:  # 买入
        # 买入时关注卖盘数据
        price_levels = [
            (bid_ask_data['卖1价'], bid_ask_data['卖1量']),
            (bid_ask_data['卖2价'], bid_ask_data['卖2量']),
            (bid_ask_data['卖3价'], bid_ask_data['卖3量']),
            (bid_ask_data['卖4价'], bid_ask_data['卖4量']),
            (bid_ask_data['卖5价'], bid_ask_data['卖5量'])
        ]

    # 过滤掉无效数据
    valid_levels = [(price, vol) for price, vol in price_levels
                    if pd.notna(price) and price != '-' and price > 0
                    and pd.notna(vol) and vol != '-' and vol > 0]

    if not valid_levels:
        return []

    order_plan = []
    remaining_quantity = target_quantity

    # 按新规则进行拆单
    for price, available_vol in valid_levels:
        if remaining_quantity <= 0:
            break

        # 如果当前档位量足够，全部买入/卖出
        if remaining_quantity <= available_vol:
            order_plan.append({
                'price': price,
                'volume': remaining_quantity * 100,
                'amount': price * remaining_quantity * 100
            })
            remaining_quantity = 0
            break
        else:
            # 当前档位量不足，买入该档位的80%
            take_volume = int(available_vol * 0.8)
            # 确保不会超过剩余需交易的数量
            take_volume = min(take_volume, remaining_quantity)

            if take_volume > 0:
                order_plan.append({
                    'price': price,
                    'volume': take_volume * 100,
                    'amount': price * take_volume * 100
                })
                remaining_quantity -= take_volume

    # 如果还有剩余未成交的数量，市价全部吃掉
    if remaining_quantity > 0:
        # 使用最优价格吃掉剩余订单
        if trade_type == '卖出':
            # 卖出使用买盘价格
            market_price = bid_ask_data.get('买1价', valid_levels[0][0])
        else:
            # 买入使用卖盘价格
            market_price = bid_ask_data.get('卖1价', valid_levels[0][0])

        # 市价成交剩余部分
        order_plan.append({
            'price': market_price,
            'volume': remaining_quantity * 100,
            'amount': market_price * remaining_quantity * 100
        })

    return order_plan


'''
def calculate_trade_quantity(row):
    """Normalize split-order quantities to shares."""
    qty = pd.to_numeric(row.get('number_of_transactions'), errors='coerce')
    if pd.notna(qty) and qty > 0:
        return int(qty)

    turnover = pd.to_numeric(row.get('turnover'), errors='coerce')
    trade_price = pd.to_numeric(row.get('trade_price'), errors='coerce')
    if pd.notna(turnover) and pd.notna(trade_price) and trade_price > 0:
        return int(turnover / trade_price)

    return 0


def split_order_strategy(row, bid_ask_data):
    """Build split orders with all quantities tracked in shares."""
    trade_type = row['trade_type']
    target_quantity = calculate_trade_quantity(row)

    if target_quantity <= 0:
        return []

    if trade_type == '鍗栧嚭':
        price_levels = [
            (bid_ask_data['涔?浠?], bid_ask_data['涔?閲?]),
            (bid_ask_data['涔?浠?], bid_ask_data['涔?閲?]),
            (bid_ask_data['涔?浠?], bid_ask_data['涔?閲?]),
            (bid_ask_data['涔?浠?], bid_ask_data['涔?閲?]),
            (bid_ask_data['涔?浠?], bid_ask_data['涔?閲?])
        ]
    else:
        price_levels = [
            (bid_ask_data['鍗?浠?], bid_ask_data['鍗?閲?]),
            (bid_ask_data['鍗?浠?], bid_ask_data['鍗?閲?]),
            (bid_ask_data['鍗?浠?], bid_ask_data['鍗?閲?]),
            (bid_ask_data['鍗?浠?], bid_ask_data['鍗?閲?]),
            (bid_ask_data['鍗?浠?], bid_ask_data['鍗?閲?])
        ]

    valid_levels = []
    for price, vol in price_levels:
        if not pd.notna(price) or price == '-' or price <= 0:
            continue
        if not pd.notna(vol) or vol == '-':
            continue

        volume_value = int(pd.to_numeric(vol, errors='coerce') or 0)
        if volume_value > 0:
            valid_levels.append((float(price), volume_value))

    if not valid_levels:
        return []

    order_plan = []
    remaining_quantity = target_quantity

    for price, available_vol in valid_levels:
        if remaining_quantity <= 0:
            break

        if remaining_quantity <= available_vol:
            order_plan.append({
                'price': price,
                'volume': remaining_quantity,
                'amount': price * remaining_quantity
            })
            remaining_quantity = 0
            break

        take_volume = min(int(available_vol * 0.8), remaining_quantity)
        if take_volume > 0:
            order_plan.append({
                'price': price,
                'volume': take_volume,
                'amount': price * take_volume
            })
            remaining_quantity -= take_volume

    if remaining_quantity > 0:
        if trade_type == '鍗栧嚭':
            market_price = bid_ask_data.get('涔?浠?, valid_levels[0][0])
        else:
            market_price = bid_ask_data.get('鍗?浠?, valid_levels[0][0])

        order_plan.append({
            'price': market_price,
            'volume': remaining_quantity,
            'amount': market_price * remaining_quantity
        })

    return order_plan
'''


def calculate_trade_quantity(row):
    """Normalize split-order quantities to shares."""
    qty = pd.to_numeric(row.get('number_of_transactions'), errors='coerce')
    if pd.notna(qty) and qty > 0:
        return int(qty)

    turnover = pd.to_numeric(row.get('turnover'), errors='coerce')
    trade_price = pd.to_numeric(row.get('trade_price'), errors='coerce')
    if pd.notna(turnover) and pd.notna(trade_price) and trade_price > 0:
        return int(turnover / trade_price)

    return 0


def split_order_strategy(row, bid_ask_data):
    """Fallback split-order plan with quantities kept in shares."""
    target_quantity = calculate_trade_quantity(row)
    if target_quantity <= 0:
        return []

    trade_price = pd.to_numeric(row.get('trade_price'), errors='coerce')
    if not pd.notna(trade_price) or trade_price <= 0:
        positive_numbers = []
        for value in bid_ask_data.values():
            numeric_value = pd.to_numeric(value, errors='coerce')
            if pd.notna(numeric_value) and numeric_value > 0:
                positive_numbers.append(float(numeric_value))
        if not positive_numbers:
            return []
        trade_price = positive_numbers[0]

    return [{
        'price': float(trade_price),
        'volume': int(target_quantity),
        'amount': float(trade_price) * int(target_quantity),
    }]


def send_order_to_api(order_list):
    """
    发送订单到交易接口
    :param order_list: 订单列表
    :return: 接口响应
    """
    url = "http://127.0.0.1:6003/api/queue"
    headers = {'Content-Type': 'application/json'}

    try:
        print("发送订单到接口...", order_list)
        response = requests.post(url, data=json.dumps(order_list), headers=headers)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"发送订单到接口时出错: {e}")
        return None


def get_bid_ask_data_with_multiple_sources(filtered_df):
    """
    从多个数据源获取盘口数据
    :param filtered_df: 包含交易信息的DataFrame
    :return: 包含盘口数据的DataFrame
    """
    result_rows = []

    for idx, row in filtered_df.iterrows():
        stock_code = row['st_code']
        # 转换股票代码格式以适应不同数据源
        if '.SH' in stock_code:
            dfcf_code = 'sh' + stock_code.split('.')[0]
            tencent_code = 'sh' + stock_code.split('.')[0]
        elif '.SZ' in stock_code:
            dfcf_code = 'sz' + stock_code.split('.')[0]
            tencent_code = 'sz' + stock_code.split('.')[0]
        else:
            dfcf_code = stock_code
            tencent_code = stock_code

        # 获取盘口数据
        bid_ask_data = fetcher.robust_gupiaopankou_get(tencent_code)

        if bid_ask_data and 'source' not in bid_ask_data:
            # 合并原始数据和盘口数据
            combined_row = row.to_dict()
            combined_row.update(bid_ask_data)
            result_rows.append(combined_row)
        else:
            # 如果获取不到盘口数据，仍然保留原始数据
            result_rows.append(row.to_dict())
            logger.warning(f"无法获取股票 {stock_code} 的盘口数据")

    return pd.DataFrame(result_rows)


def execute_split_orders(filtered_df):
    """
    执行拆单交易 - 逐个股票处理并发送到交易接口
    :param filtered_df: 包含交易信息的DataFrame
    :return: 执行结果DataFrame
    """
    print("开始逐个执行拆单交易...")
    executed_results = []
    start_time = datetime.now()

    # 逐个处理每只股票
    for idx, row in filtered_df.iterrows():
        stock_code = row['st_code']
        trade_type = row['trade_type']
        target_price = row['trade_price']
        trade_date = row['trade_date']

        print(f"\n处理股票: {stock_code}")

        # 为单只股票创建DataFrame
        single_stock_df = pd.DataFrame([row])

        # 从数据源获取该股票的盘口数据
        result_df = get_bid_ask_data_with_multiple_sources(single_stock_df)

        if result_df.empty or result_df.iloc[0].isnull().all():
            print(f"无法获取股票 {stock_code} 的盘口数据")
            executed_results.append({
                'stock_code': stock_code,
                'trade_type': trade_type,
                'trade_date': trade_date,
                'target_price': target_price,
                'executed_volume': 0,
                'executed_turnover': 0,
                'avg_price': None,
                'executed_trades': 0,
                'start_time': start_time,
                'end_time': datetime.now()
            })
            continue

        stock_row = result_df.iloc[0]

        # 获取该股票的盘口数据
        bid_ask_data = {
            '买1价': stock_row.get('买1价', 0), '买1量': stock_row.get('买1量', 0),
            '买2价': stock_row.get('买2价', 0), '买2量': stock_row.get('买2量', 0),
            '买3价': stock_row.get('买3价', 0), '买3量': stock_row.get('买3量', 0),
            '买4价': stock_row.get('买4价', 0), '买4量': stock_row.get('买4量', 0),
            '买5价': stock_row.get('买5价', 0), '买5量': stock_row.get('买5量', 0),
            '卖1价': stock_row.get('卖1价', 0), '卖1量': stock_row.get('卖1量', 0),
            '卖2价': stock_row.get('卖2价', 0), '卖2量': stock_row.get('卖2量', 0),
            '卖3价': stock_row.get('卖3价', 0), '卖3量': stock_row.get('卖3量', 0),
            '卖4价': stock_row.get('卖4价', 0), '卖4量': stock_row.get('卖4量', 0),
            '卖5价': stock_row.get('卖5价', 0), '卖5量': stock_row.get('卖5量', 0)
        }

        # 生成拆单计划
        print(f"生成 {stock_code} 的拆单计划...")
        order_plan = split_order_strategy(stock_row, bid_ask_data)
        print(f"{stock_code} 拆单计划: {order_plan}")

        if not order_plan:
            # 没有可行的拆单计划
            executed_results.append({
                'stock_code': stock_code,
                'trade_type': trade_type,
                'trade_date': trade_date,
                'target_price': target_price,
                'executed_volume': 0,
                'executed_turnover': 0,
                'avg_price': None,
                'executed_trades': 0,
                'start_time': start_time,
                'end_time': datetime.now()
            })
            continue

        # 构造发送到API的订单列表
        api_order_list = []
        strategy_no = "1002"  # 默认策略编号，可根据需要修改
        stock_name = stock_code  # 使用股票代码作为名称，实际应用中可查询股票名称

        for order in order_plan:
            # 根据交易类型确定操作方向
            operate = "sell" if trade_type == "卖出" else "buy"

            api_order = {
                "strategy_no": strategy_no,
                "code": stock_code.split('.')[0],  # 去除股票代码中的后缀（如.SH）
                "name": stock_name,
                "price": order['price'],
                "ct_amount": order['volume'],
                "operate": operate
            }
            api_order_list.append(api_order)

        # 发送订单到交易接口（逐个股票发送）
        print(f"发送 {stock_code} 的订单到交易接口...")
        api_response = send_order_to_api(api_order_list)
        print(f"{stock_code} 接口响应: {api_response}")

        # 模拟执行订单
        total_volume = 0
        total_turnover = 0
        executed_trades = len(order_plan)

        for order in order_plan:
            total_volume += order['volume']
            total_turnover += order['amount']
            # 模拟订单执行延迟
            time.sleep(random.uniform(0.5, 1))

        # 计算平均价格
        avg_price = total_turnover / total_volume if total_volume > 0 else None

        executed_results.append({
            'stock_code': stock_code,
            'trade_type': trade_type,
            'trade_date': trade_date,
            'target_price': target_price,
            'executed_volume': total_volume,
            'executed_turnover': total_turnover,
            'avg_price': avg_price,
            'executed_trades': executed_trades,
            'start_time': start_time,
            'end_time': datetime.now()
        })

        # 股票间的时间间隔
        time.sleep(random.uniform(1, 2))

    # 转换为DataFrame
    executed_df = pd.DataFrame(executed_results)
    return executed_df


def save_to_database(executed_df, connection=None):
    """
    将执行结果保存到数据库
    :param executed_df: 执行结果DataFrame
    :param connection: 数据库连接（如果需要实际保存到数据库）
    """
    # 这里只是示例，实际使用时需要连接到数据库并执行INSERT语句
    print("准备保存到数据库的执行结果:")
    print(executed_df)

    # 如果有数据库连接，可以使用如下代码:
    engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    executed_df.to_sql("executed_trades", engine, if_exists="append", index=False, chunksize=10000, method="multi")


# 使用示例
if __name__ == '__main__':
    # 创建示例数据
    sample_data = {
        'st_code': ['000001.SZ', '600792.SH'],
        'trade_date': ['2025-11-20', '2025-11-20'],
        'trade_type': ['买入', '卖出'],
        'trade_price': [11.26, 3.92],
        'number_of_transactions': [100, 258],  # 50手，30手
        'turnover': [None, None]  # 可以为空，因为我们有手数
    }

    filtered_df = pd.DataFrame(sample_data)

    # 执行拆单交易
    print("开始执行拆单交易...")
    executed_result = execute_split_orders(filtered_df)

    # 显示结果
    print("\n拆单执行结果:")
    print(executed_result)

    # 保存到数据库（示例）
    # save_to_database(executed_result)
