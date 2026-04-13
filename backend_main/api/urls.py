from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.hello_world),
    path('health/', views.health_check),
]
