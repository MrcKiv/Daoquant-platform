# user/decorators.py
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from .models import User


def permission_required(required_level):
    """
    权限检查装饰器
    required_level: 所需权限等级 ('free', 'basic', 'premium', 'vip', 'admin')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 检查用户是否登录（通过session）
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'error': '请先登录'}, status=401)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'error': '用户不存在'}, status=401)

            # 检查会员是否过期并更新状态
            if (user.membership_expiry and
                    user.membership_expiry < timezone.now() and
                    user.membership_level not in ('free', 'admin')):
                user.membership_level = 'free'
                user.membership_expiry = None
                user.save()

            # 检查权限
            if not user.has_permission(required_level):
                return JsonResponse({
                    'error': f'需要{required_level}及以上权限',
                    'current_level': user.membership_level,
                    'required_level': required_level
                }, status=403)

            # 将用户对象添加到request中供视图使用
            request.user = user
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
