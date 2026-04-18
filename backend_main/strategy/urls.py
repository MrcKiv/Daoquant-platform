from django.urls import path

from . import safe_views, views, views_多图
from .views import csrf_token_view, newConstruction

urlpatterns = [
    path('getStrategyConfig/', safe_views.get_strategy_config, name='get_strategy_config'),
    path('loadStrategySummary/', views.loadStrategyConfig, name='loadStrategySummary'),
    path('loadStrategyConfig/', views_多图.loadStrategyConfig, name='loadStrategyConfig'),
    path('public_strategy/', safe_views.public_strategy, name='publicStrategy'),
    path('getStockSelector/', safe_views.get_stock_selector, name='get_stock_selector'),
    path('listUploadedStrategies/', safe_views.list_uploaded_strategy_files, name='list_uploaded_strategies'),
    path('uploadStrategyFile/', safe_views.upload_strategy_file, name='upload_strategy_file'),
    path('getUserStrategies/', views.getUserStrategies, name='get_user_strategies'),
    path('subscribeStrategy/', views.subscribeStrategy, name='subscribe_strategy'),
    path('getFactorConfig/', safe_views.get_factor_config, name='get_factor_config'),
    path('insert_name/', safe_views.insert_name, name='insert_name'),
    path('delete_strategy/', safe_views.delete_strategy, name='delete_strategy'),
    path('getBackTrigger/', views.getBackTrigger),
    path('getBacktestLog/', views.getBacktestLog, name='get_backtest_log'),
    path('newconstruction/', newConstruction.as_view(), name='new_construction'),
    path('csrf_token/', csrf_token_view),
    path('trigger-daily-backtest/', views.trigger_daily_backtest, name='trigger_daily_backtest'),
    path('trigger-single-backtest/', views.trigger_single_backtest, name='trigger_single_backtest'),
    path('queryClosePrice/', views.queryClosePrice, name='queryClosePrice'),
    path('getKlineChart/', views.getKlineChart, name='getKlineChart'),
    path('getSimilar/', views.getSimilar, name='getSimilar'),
    path('getBase/', views.getBase, name='getBase'),
    path('getSingleStock/', views.getSingleStock, name='getSingleStock'),
    path('getSimilarStock/', views.getSimilarStock, name='getSimilarStock'),
]
