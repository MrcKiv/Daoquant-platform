# ths_trade/applications/trade/Multi_Account_Manager.py

from applications.trade.server.THS_Trader_Server import THSTraderServer
from applications import API_Config
import threading
import time


class MultiAccountManager:
    def __init__(self):
        self.accounts = {}
        self._init_accounts()

    def _init_accounts(self):
        """初始化所有账户"""
        for account_name, config in API_Config.ACCOUNT_CONFIGS.items():
            try:
                trader = THSTraderServer(config)
                self.accounts[account_name] = {
                    'trader': trader,
                    'config': config,
                    'status': 'connected'
                }
                print(f"账户 {account_name} 初始化成功")
            except Exception as e:
                print(f"账户 {account_name} 初始化失败: {e}")
                self.accounts[account_name] = {
                    'trader': None,
                    'config': config,
                    'status': 'disconnected'
                }

    def get_account(self, account_name):
        """获取指定账户的交易器"""
        if account_name in self.accounts:
            return self.accounts[account_name]['trader']
        return None

    def execute_trade(self, account_name, trade_data):
        """在指定账户执行交易"""
        trader = self.get_account(account_name)
        if trader is None:
            return {"success": False, "msg": f"账户 {account_name} 未连接"}

        try:
            if trade_data['operate'] == 'buy':
                return trader.buy(trade_data)
            elif trade_data['operate'] == 'sell':
                return trader.sell(trade_data)
            else:
                return {"success": False, "msg": "不支持的操作类型"}
        except Exception as e:
            return {"success": False, "msg": f"交易执行失败: {e}"}

    def get_all_accounts_status(self):
        """获取所有账户状态"""
        status = {}
        for name, account_info in self.accounts.items():
            status[name] = account_info['status']
        return status


# 全局账户管理器实例
account_manager = MultiAccountManager()
