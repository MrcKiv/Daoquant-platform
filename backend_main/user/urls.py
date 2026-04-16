from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('login/', views.login),
    path('logout/', views.logout),
    path('admin/login/', views.admin_login),
    path('admin/users/', views.admin_users),
    path('admin/users/<uuid:user_id>/', views.admin_delete_user),
    path('admin/users/<uuid:user_id>/membership/', views.admin_update_user_level),
    path('admin/users/<uuid:user_id>/password/', views.admin_update_user_password),
    # path('profile/', views.user_profile),
    path('check_login/', views.check_login),
]
