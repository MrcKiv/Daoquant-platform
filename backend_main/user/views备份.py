from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.http import JsonResponse
from django.contrib.sessions.models import Session
from .models import User
import json
import uuid


@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(" 接收到前端数据：", data)

        usernumber = data.get('usernumber')
        password = data.get('password')
        name = data.get('name')
        id = str(uuid.uuid4())  # 生成唯一ID

        print(f" 解析字段：usernumber={usernumber}, password={password}, name={name}， id={id}")

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

        User.objects.create(id = id, usernumber=usernumber, password=password, name=name)
        print(" 成功写入数据库！")
        return JsonResponse({'msg': '注册成功'})


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
                'id': user.id,
                'name': user.name,
                'usernumber': user.usernumber
            }
        })

        # 只设置CORS头，让Django自动处理Cookie
        response["Access-Control-Allow-Origin"] = "http://192.168.2.92:5173"
        response["Access-Control-Allow-Credentials"] = "true"

        return response


@csrf_exempt
def check_login(request):
    if request.method == 'GET':
        # 获取 session 中的信息
        user_id = request.session.get('user_id')
        print(" user_id: ", user_id)
        if user_id:
            return JsonResponse({'is_login': True, 'user_id': user_id})
        else:
            return JsonResponse({'is_login': False, 'error': '未登录'}, status=401)
def user_profile(request):
    # 示例逻辑：返回固定的个人信息
    return JsonResponse({
        'name': '测试用户',
        'msg': '这是一个示例的用户信息接口'
    })
