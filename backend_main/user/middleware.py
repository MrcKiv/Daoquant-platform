# middleware.py
class SameSiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 检查是否为登录响应
        if hasattr(response, 'cookies'):
            for cookie in response.cookies.values():
                # 为所有 Cookie 设置 SameSite=None 和 Secure
                cookie['samesite'] = 'None'
                cookie['secure'] = True

        return response