# 导入模块
from django.shortcuts import render, redirect, reverse
from django.views import View
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
import json
# 导入自定义forms表单，使用RegisterForm方法，使用LoginForm方法
from .forms import RegisterForm, LoginForm
# 导入自定义的模型users方法
from .models import Users
# 导入django自带的login、logout方法
from django.contrib.auth import login, logout

# Create your views here.

# 继承类视图View
# 注册功能
class RegisterView(View):
    '''
    这里写上访问路径
    127.0.0.1:8888/users/register/
    '''
    def get(self, request):
        # 渲染出注册页面
        return render(request, 'users/register.html')

    # 注册功能
    def post(self, request):
        # 获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 验证参数
        form = RegisterForm(data=dict_data) # 把前端拿到的输入内容传送到form中
        # 判断如果表单验证是否通过,如果通过验证，就保存
        if form.is_valid():
            # 拿到通过验证了的数据
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            mobile = form.cleaned_data.get('mobile')
            # 创建数据
            user = Users.object.create_user(username=username,password=password,mobile=mobile)
            # 使用django自带的login方法（自动保存session）
            login(request, user)
            # 返回前端
            return to_json_data(errmsg='恭喜~注册成功！')
        # 不能通过前面的form表单验证时
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 登录功能
class LoginView(View):
    '''
    # 传参数-账号、密码、记住你
    # 请求方式：POST，涉及到敏感信息和库联系
    # 提交方式：ajax(form也可以)
    '''
    # 首先是渲染出一个大家能看到的页面
    def get(self, request):
        return render(request, 'users/login.html')

    # 登录
    def post(self, request):
        '''
        # 获取参数
            - 熟悉的配方
        # 校验参数
            - 账号是否符合要求、是否为空
            - 账号密码是否与数据库里面的一致
        # 返回前端
        '''
        # 获取参数
        json_data = request.body  # 使用body方法拿到页面用户输入的内容，是byte格式的
        # 判断是否拿到页面的内容
        if not json_data:   # 如果拿不到就报错
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 如果拿到内容就解码且转换成字典格式
        dict_data = json.loads(json_data.decode('utf-8'))

        # 校验参数
        form = LoginForm(data=dict_data, request=request) # 把前端拿到的参数传到form表单进行检验，同时把request也一起给过去

        # 返回前端
        if form.is_valid():
            return to_json_data(errmsg='恭喜！，登录成功~')
        # 不能通过前面的form表单验证时
        else:
        # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 退出功能
class LogoutView(View):
    '''

    '''
    def get(self,request):
        logout(request) # 就是自动删除session-id
        # 重定向到登录页面
        return redirect(reverse('users:login'))