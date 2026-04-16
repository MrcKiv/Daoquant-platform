# user/views.py
import json

from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from .decorators import permission_required
from .models import User


DEFAULT_ADMIN_USERNUMBER = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin'
DEFAULT_ADMIN_NAME = '系统管理员'
ALLOWED_MEMBERSHIP_LEVELS = {level for level, _ in User.MEMBERSHIP_LEVELS}


def _parse_json(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _user_payload(user):
    return {
        'id': str(user.id),
        'name': user.name,
        'usernumber': user.usernumber,
        'membership_level': user.membership_level,
        'membership_expiry': user.membership_expiry.isoformat() if user.membership_expiry else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
    }


def _start_session(request, user):
    request.session.cycle_key()
    request.session['user_id'] = str(user.id)
    request.session['user_name'] = user.name
    request.session['usernumber'] = user.usernumber
    request.session.save()
    return request.session.session_key


def _authenticate_user(usernumber, password):
    if not usernumber or not password:
        return None, JsonResponse({'msg': '账号和密码不能为空'}, status=400)

    try:
        user = User.objects.get(usernumber=usernumber)
    except User.DoesNotExist:
        return None, JsonResponse({'msg': '账号不存在'}, status=404)

    if user.password != password:
        return None, JsonResponse({'msg': '密码错误'}, status=401)

    return user, None


def _is_valid_usernumber(usernumber, allow_default_admin=False):
    if allow_default_admin and usernumber == DEFAULT_ADMIN_USERNUMBER:
        return True
    return isinstance(usernumber, str) and usernumber.isdigit() and len(usernumber) == 11


def _ensure_default_admin_user():
    user = User.objects.filter(usernumber=DEFAULT_ADMIN_USERNUMBER).first()
    if user is not None:
        updated = False
        if user.membership_level != 'admin':
            user.membership_level = 'admin'
            updated = True
        if user.membership_expiry is not None:
            user.membership_expiry = None
            updated = True
        if not user.name:
            user.name = DEFAULT_ADMIN_NAME
            updated = True
        if updated:
            user.save()
        return user

    return User.objects.create(
        usernumber=DEFAULT_ADMIN_USERNUMBER,
        password=DEFAULT_ADMIN_PASSWORD,
        name=DEFAULT_ADMIN_NAME,
        membership_level='admin',
        membership_expiry=None,
    )


def _get_target_user(user_id):
    try:
        return User.objects.get(id=user_id), None
    except User.DoesNotExist:
        return None, JsonResponse({'msg': '用户不存在'}, status=404)


def register(request):
    return JsonResponse({'msg': '系统已关闭注册功能，请联系管理员开通账号'}, status=403)


@ensure_csrf_cookie
def login(request):
    if request.method != 'POST':
        return JsonResponse({'msg': '仅支持POST请求'}, status=405)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({'msg': '请求体不是有效的JSON'}, status=400)

    usernumber = data.get('usernumber')
    password = data.get('password')
    user, error_response = _authenticate_user(usernumber, password)
    if error_response:
        return error_response

    session_key = _start_session(request, user)
    return JsonResponse({
        'msg': '登录成功',
        'token': session_key,
        'user': _user_payload(user),
    })


def logout(request):
    if request.method != 'POST':
        return JsonResponse({'msg': '仅支持POST请求'}, status=405)

    request.session.flush()
    return JsonResponse({'msg': '退出登录成功'})


@ensure_csrf_cookie
def admin_login(request):
    if request.method != 'POST':
        return JsonResponse({'msg': '仅支持POST请求'}, status=405)

    _ensure_default_admin_user()

    data = _parse_json(request)
    if data is None:
        return JsonResponse({'msg': '请求体不是有效的JSON'}, status=400)

    usernumber = data.get('usernumber')
    password = data.get('password')
    user, error_response = _authenticate_user(usernumber, password)
    if error_response:
        return error_response

    if user.membership_level != 'admin':
        return JsonResponse({'msg': '仅管理员账号可以登录管理后台'}, status=403)

    session_key = _start_session(request, user)
    return JsonResponse({
        'msg': '管理员登录成功',
        'token': session_key,
        'user': _user_payload(user),
    })


def check_login(request):
    if request.method != 'GET':
        return JsonResponse({'msg': '仅支持GET请求'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'is_login': False, 'error': '未登录'}, status=401)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'is_login': False, 'error': '用户不存在'}, status=401)

    return JsonResponse({
        'is_login': True,
        'user': _user_payload(user),
    })


@permission_required('admin')
def admin_users(request):
    if request.method == 'GET':
        users = User.objects.all().order_by('-created_at')
        return JsonResponse({
            'users': [_user_payload(user) for user in users],
            'membership_levels': [
                {'value': value, 'label': label}
                for value, label in User.MEMBERSHIP_LEVELS
            ],
        })

    if request.method != 'POST':
        return JsonResponse({'msg': '仅支持GET或POST请求'}, status=405)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({'msg': '请求体不是有效的JSON'}, status=400)

    usernumber = (data.get('usernumber') or '').strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()
    membership_level = data.get('membership_level') or 'free'

    if not (usernumber and password and name):
        return JsonResponse({'msg': '缺少字段'}, status=400)

    if membership_level not in ALLOWED_MEMBERSHIP_LEVELS:
        return JsonResponse({'msg': '无效的账号级别'}, status=400)

    if not _is_valid_usernumber(usernumber, allow_default_admin=False):
        return JsonResponse({'msg': '账号必须是11位纯数字'}, status=400)

    if User.objects.filter(usernumber=usernumber).exists():
        return JsonResponse({'msg': '账号已存在'}, status=400)

    if User.objects.filter(name=name).exists():
        return JsonResponse({'msg': '用户名已存在'}, status=400)

    user = User.objects.create(
        usernumber=usernumber,
        password=password,
        name=name,
        membership_level=membership_level,
        membership_expiry=None,
    )

    return JsonResponse({
        'msg': '账号创建成功',
        'user': _user_payload(user),
    })


@permission_required('admin')
def admin_update_user_level(request, user_id):
    if request.method not in ('PATCH', 'POST'):
        return JsonResponse({'msg': '仅支持PATCH或POST请求'}, status=405)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({'msg': '请求体不是有效的JSON'}, status=400)

    membership_level = data.get('membership_level')
    if membership_level not in ALLOWED_MEMBERSHIP_LEVELS:
        return JsonResponse({'msg': '无效的账号级别'}, status=400)

    target_user, error_response = _get_target_user(user_id)
    if error_response:
        return error_response

    if target_user.usernumber == DEFAULT_ADMIN_USERNUMBER and membership_level != 'admin':
        return JsonResponse({'msg': '默认管理员账号不能移出admin级别'}, status=400)

    if str(target_user.id) == str(request.user.id) and membership_level != 'admin':
        return JsonResponse({'msg': '当前登录管理员不能取消自己的admin权限'}, status=400)

    target_user.membership_level = membership_level
    if membership_level in ('free', 'admin'):
        target_user.membership_expiry = None
    target_user.save()

    return JsonResponse({
        'msg': '账号级别更新成功',
        'user': _user_payload(target_user),
    })


@permission_required('admin')
def admin_update_user_password(request, user_id):
    if request.method not in ('PATCH', 'POST'):
        return JsonResponse({'msg': '仅支持PATCH或POST请求'}, status=405)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({'msg': '请求体不是有效的JSON'}, status=400)

    password = data.get('password')
    if not isinstance(password, str) or not password.strip():
        return JsonResponse({'msg': '新密码不能为空'}, status=400)

    target_user, error_response = _get_target_user(user_id)
    if error_response:
        return error_response

    target_user.password = password.strip()
    target_user.save()

    return JsonResponse({
        'msg': '账号密码修改成功',
        'user': _user_payload(target_user),
    })


@permission_required('admin')
def admin_delete_user(request, user_id):
    if request.method not in ('DELETE', 'POST'):
        return JsonResponse({'msg': '仅支持DELETE或POST请求'}, status=405)

    target_user, error_response = _get_target_user(user_id)
    if error_response:
        return error_response

    if target_user.usernumber == DEFAULT_ADMIN_USERNUMBER:
        return JsonResponse({'msg': '默认管理员账号不能删除'}, status=400)

    if str(target_user.id) == str(request.user.id):
        return JsonResponse({'msg': '当前登录管理员不能删除自己'}, status=400)

    deleted_user = _user_payload(target_user)
    target_user.delete()

    return JsonResponse({
        'msg': '账号删除成功',
        'user': deleted_user,
    })
