# ths_trade/applications/api/handlers/Trade_API.py
from common.CommonHandler import CommonHandler
from trest.router import post, get, options
import json
from applications.work_queue.ActiveWork import ActiveWork
from applications.api.business.Queue_Business import InputQueue
aw = ActiveWork()


class QueueHandler(CommonHandler):
    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', '*')  # 生产环境建议指定具体域名
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with, content-type')
        self.set_header('Access-Control-Max-Age', '3600')

    def options(self, *args, **kwargs):
        # 处理预检请求
        self.set_status(204)
        self.finish()

    @post('queue')
    def queue(self):
        """ 处理交易队列请求 """
        try:
            # 获取调用接口的传参
            request_str = self.request.body
            data_list = json.loads(request_str) if isinstance(request_str, str) else request_str

            if isinstance(data_list, str):
                data_list = json.loads(data_list)

            # 处理交易数据并加入队列

            InputQueue(json.dumps(data_list) if isinstance(data_list, list) else request_str)

            res_json = {"success": True, "message": "交易指令已接收"}
            return self.isOk(res_json)

        except Exception as e:
            return self.isFail(str(e), 400)

    @get('queue')
    def get_queue(self):
        """ 获取队列状态 """
        try:
            # 返回队列状态信息
            res_json = {"success": True, "message": "服务运行正常"}
            return self.isOk(res_json)
        except Exception as e:
            return self.isFail(str(e), 400)
