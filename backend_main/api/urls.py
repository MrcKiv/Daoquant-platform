from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.hello_world),
    path('health/', views.health_check),
    path('stock-backfill/status/', views.stock_backfill_status),
    path('stock-backfill/start/', views.stock_backfill_start),
]
