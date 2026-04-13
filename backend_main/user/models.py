# user/models.py
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(models.Model):
    MEMBERSHIP_LEVELS = [
        ('free', '免费用户'),
        ('basic', '基础会员'),
        ('premium', '高级会员'),
        ('vip', 'VIP会员')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usernumber = models.CharField(max_length=20, unique=True)  # 账号
    password = models.CharField(max_length=128)  # 密码
    name = models.CharField(max_length=50)  # 姓名

    # 权限相关字段
    membership_level = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_LEVELS,
        default='free'
    )
    membership_expiry = models.DateTimeField(null=True, blank=True)

    # 注册时间
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_user'


    def __str__(self):
        return f"{self.name} ({self.usernumber})"

    def is_vip_active(self):
        """检查VIP权限是否有效"""
        if self.membership_level == 'free':
            return False
        if not self.membership_expiry:
            return True  # 永久会员
        return self.membership_expiry > timezone.now()

    def has_permission(self, required_level):
        """检查用户是否有足够权限"""
        level_hierarchy = {
            'free': 0,
            'basic': 1,
            'premium': 2,
            'vip': 3
        }

        if not self.is_vip_active():
            return level_hierarchy.get('free', 0) >= level_hierarchy.get(required_level, 0)

        user_level = level_hierarchy.get(self.membership_level, 0)
        required_level_value = level_hierarchy.get(required_level, 0)
        return user_level >= required_level_value


# 订阅记录表
class UserSubscription(models.Model):
    SUBSCRIPTION_TYPES = [
        ('monthly', '月付'),
        ('quarterly', '季付'),
        ('yearly', '年付'),
        ('lifetime', '终身')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'user_usersubscription'

    def save(self, *args, **kwargs):
        # 自动计算结束日期
        if not self.end_date and self.subscription_type != 'lifetime':
            if self.subscription_type == 'monthly':
                self.end_date = timezone.now() + timedelta(days=30)
            elif self.subscription_type == 'quarterly':
                self.end_date = timezone.now() + timedelta(days=90)
            elif self.subscription_type == 'yearly':
                self.end_date = timezone.now() + timedelta(days=365)
        elif self.subscription_type == 'lifetime':
            self.end_date = None  # 终身会员没有结束日期

        super().save(*args, **kwargs)

    def is_expired(self):
        if self.subscription_type == 'lifetime':
            return False
        return self.end_date and timezone.now() > self.end_date