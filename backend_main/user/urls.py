from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('login/', views.login),
    # path('profile/', views.user_profile),
    path('check_login/', views.check_login),
]
