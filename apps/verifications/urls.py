# 导入模块
from django.urls import path, re_path
from verifications import views

# 定义app名字
app_name = 'verifications'

urlpatterns = [
    # 定义注册页面的路由
    path('image_codes/<uuid:image_code_id>/', views.ImageCode.as_view(), name='image_code'),
    # 使用正则，可以在url中多进行一次验证
    re_path('usernames/(?P<username>\w{5,20})/', views.CheckUsernameView.as_view(), name='check_username'),
    re_path('mobiles/(?P<mobile>1[3-9]\d{9})/', views.CheckMobileView.as_view(), name='check_mobile'),
    re_path('sms_codes/', views.SmsCodesView.as_view(), name='sms_codes'),
]