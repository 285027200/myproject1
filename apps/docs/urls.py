# 导入路径模块和视图
from django.urls import path
from docs import views

app_name = 'doc'

urlpatterns = [
    path('', views.doc_index, name='index'),
    path('<int:doc_id>/', views.DocDownload.as_view(), name='doc_download'),
]