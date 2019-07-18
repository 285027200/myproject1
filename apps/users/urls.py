# 导入模块
from django.urls import path
from users import views

# 定义app名字
app_name = 'users'

urlpatterns = [
    # 定义注册页面的路由
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]