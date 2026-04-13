# user/views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.sessions.models import Session

from .decorators import permission_required
from .models import User
import json
import uuid
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@csrf_exempt
# @permission_required('basic')
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(" 接收到前端数据：", data)

        usernumber = data.get('usernumber')
        password = data.get('password')
        name = data.get('name')

        print(f" 解析字段：usernumber={usernumber}, password={password}, name={name}")

        if not (usernumber and password and name):
            print(" 缺少字段")
            return JsonResponse({'msg': '缺少字段'}, status=400)

        if not usernumber.isdigit() or len(usernumber) != 11:
            print(" 账号格式错误")
            return JsonResponse({'msg': '账号必须是11位纯数字'}, status=400)

        if User.objects.filter(usernumber=usernumber).exists():
            print(" 账号已存在")
            return JsonResponse({'msg': '账号已存在'}, status=400)

        if User.objects.filter(name=name).exists():
            print(" 用户名已存在")
            return JsonResponse({'msg': '用户名已存在'}, status=400)

        # 创建用户，默认为免费用户
        user = User.objects.create(
            usernumber=usernumber,
            password=password,
            name=name,
            membership_level='free'  # 注册默认为免费用户
        )

        print(" 成功写入数据库！")
        return JsonResponse({
            'msg': '注册成功',
            'user': {
                'id': str(user.id),
                'name': user.name,
                'usernumber': user.usernumber,
                'membership_level': user.membership_level
            }
        })


@ensure_csrf_cookie
def login(request):
    print("登录")
    if request.method == 'POST':
        data = json.loads(request.body)
        usernumber = data.get('usernumber')
        password = data.get('password')

        if not usernumber or not password:
            return JsonResponse({'msg': '账号和密码不能为空'}, status=400)

        try:
            user = User.objects.get(usernumber=usernumber)
        except User.DoesNotExist:
            return JsonResponse({'msg': '账号不存在'}, status=404)

        if user.password != password:
            return JsonResponse({'msg': '密码错误'}, status=401)

        # 登录成功：设置session
        request.session['user_id'] = str(user.id)
        request.session['user_name'] = user.name
        request.session['usernumber'] = user.usernumber

        # 确保session保存
        request.session.save()
        session_key = request.session.session_key
        print("session_key: ", session_key)

        # 创建响应对象
        response = JsonResponse({
            'msg': '登录成功',
            'token': session_key,
            'user': {
                'id': str(user.id),
                'name': user.name,
                'usernumber': user.usernumber,
                'membership_level': user.membership_level,
                'membership_expiry': user.membership_expiry.isoformat() if user.membership_expiry else None
            }
        })

        # 移除手动设置的CORS头，由 corsheaders 中间件统一管理
        # response["Access-Control-Allow-Origin"] = "http://192.168.2.92:5173"
        # response["Access-Control-Allow-Credentials"] = "true"

        return response


@csrf_exempt
def check_login(request):
    if request.method == 'GET':
        # 获取 session 中的信息
        user_id = request.session.get('user_id')
        print(" user_id: ", user_id)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                return JsonResponse({
                    'is_login': True,
                    'user': {
                        'id': str(user.id),
                        'name': user.name,
                        'usernumber': user.usernumber,
                        'membership_level': user.membership_level,
                        'membership_expiry': user.membership_expiry.isoformat() if user.membership_expiry else None
                    }
                })
            except User.DoesNotExist:
                return JsonResponse({'is_login': False, 'error': '用户不存在'}, status=401)
        else:
            return JsonResponse({'is_login': False, 'error': '未登录'}, status=401)
