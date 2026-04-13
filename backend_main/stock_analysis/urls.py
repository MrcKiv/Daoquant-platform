from django.urls import path
from . import views

app_name = 'stock_analysis'

urlpatterns = [
    # 股票搜索
    path('search/', views.search_stocks_api, name='search_stocks'),
    
    # 获取股票信息
    path('stock/<str:code>/', views.get_stock_info_api, name='get_stock_info'),
    
    # 获取指数数据
    path('index/', views.get_index_data_api, name='get_index_data'),
    
    # 获取特定指数图表数据
    path('index/<str:st_code>/', views.get_index_chart_data_api, name='get_index_chart'),
    
    # 获取股票图表数据
    path('chart/<str:code>/', views.get_stock_chart_data_api, name='get_stock_chart'),
]