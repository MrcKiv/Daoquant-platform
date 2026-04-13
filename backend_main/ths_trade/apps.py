# ths_trade/apps.py
import os
import sys
import threading
from django.apps import AppConfig


class ThsTradeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ths_trade'

    def ready(self):
        """
        Django 启动时的入口。
        规则：
        1. 只在 RUN_MAIN=true 的进程中执行（防止 autoreload 启动两次）
        2. 只有显式设置 ENABLE_TRADE=1 时才启动交易服务
        """
        # 只在 Django 的主运行进程中执行
        if os.environ.get("RUN_MAIN") != "true":
            return

        # 默认不开启交易服务，必须显式启用
        if os.environ.get("ENABLE_TRADE", "0") != "1":
            print("[ths_trade] Trade service disabled (ENABLE_TRADE=0)")
            return

        self.start_trade_service()

    def start_trade_service(self):
        """
        启动股票交易服务（Tornado）
        """
        def run_trade_service():
            try:
                app_path = os.path.dirname(__file__)

                # 确保 trest 模块路径正确
                paths_to_add = [
                    app_path,
                    os.path.join(app_path, 'trest'),
                ]

                for path in reversed(paths_to_add):
                    if path not in sys.path:
                        sys.path.insert(0, path)

                from trest.webserver import run
                import applications.Timer_Exec_Trade

                print("[ths_trade] Trade service starting...")
                run()
            except Exception as e:
                print(f"[ths_trade] Trade service failed: {e}")
                import traceback
                traceback.print_exc()

        trade_thread = threading.Thread(
            target=run_trade_service,
            daemon=True
        )
        trade_thread.start()

        print("[ths_trade] Trade service thread started")
