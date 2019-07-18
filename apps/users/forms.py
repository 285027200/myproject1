# 导入模块
import re
from django import forms
from verifications.constants import SMS_CODE_NUMS
from django_redis import get_redis_connection
from .models import Users
# 导入django自带的Q方法(能把两个参数一起查询)
from django.db.models import Q
# 导入django自带的login方法
from django.contrib.auth import login
# 导入常量
from .import constants

# 注册模型
class RegisterForm(forms.Form):
    """
    """
    username = forms.CharField(label='用户名',
                               max_length=20,
                               min_length=5,
                               error_messages={"min_length": "用户名长度要大于5", "max_length": "用户名长度要小于20",
                                               "required": "用户名不能为空"}
                               )
    password = forms.CharField(label='密码',
                               max_length=20,
                               min_length=6,
                               error_messages={"min_length": "密码长度要大于6", "max_length": "密码长度要小于20",
                                               "required": "密码不能为空"}
                               )
    password_repeat = forms.CharField(label='确认密码',
                                      max_length=20,
                                      min_length=6,
                                      error_messages={"min_length": "密码长度要大于6", "max_length": "密码长度要小于20",
                                                      "required": "密码不能为空"}
                                      )
    mobile = forms.CharField(label='手机号',
                             max_length=11,
                             min_length=11,
                             error_messages={"min_length": "手机号长度有误", "max_length": "手机号长度有误",
                                             "required": "手机号不能为空"})

    sms_code = forms.CharField(label='短信验证码',
                               max_length=SMS_CODE_NUMS,
                               min_length=SMS_CODE_NUMS,
                               error_messages={"min_length": "短信验证码长度有误", "max_length": "短信验证码长度有误",
                                               "required": "短信验证码不能为空"})

    # 校验单个字段mobile
    def clean_mobile(self):
        """
        """
        # 针对手机号来验证，先拿到用户前端输入的手机号
        tel = self.cleaned_data.get('mobile')
        # 使用正则判断手机号格式
        if not re.match(r"^1[3-9]\d{9}$", tel):
            # 如果不符合规则就报告信息
            raise forms.ValidationError("手机号码格式不正确")
        # 使用自定义的models的方法判断手机号是否已经在数据库了
        if Users.object.filter(mobile=tel).exists():
            # 如果已经存在就报告
            raise forms.ValidationError("手机号已注册，请重新输入！")
        # 最后返回用户输入的手机号
        return tel

    # 重写clean方法，联合验证
    def clean(self):
        """
        """
        # 继承重写
        cleaned_data = super().clean()
        # 拿到用户前端输入的密码
        passwd = cleaned_data.get('password')
        # 拿到用户前端输入的二次密码
        passwd_repeat = cleaned_data.get('password_repeat')
        # 判断两次密码是否一致
        if passwd != passwd_repeat:
            # 不一致就报告
            raise forms.ValidationError("两次密码不一致")
        # 拿到用户前端输入的手机号
        tel = cleaned_data.get('mobile')
        # 拿到用户前端输入的短信验证码的答案
        sms_text = cleaned_data.get('sms_code')

        # 建立redis连接
        redis_conn = get_redis_connection(alias='verify_codes')
        # 构造键
        sms_fmt = "sms_{}".format(tel)  # 如果用户输入的号码tel已经实行了发送验证码的操作的话，那这个地方构造的键就是必然存在redis中的
        # 从redis中拿取键为sms_fmt的值，并赋值给real_sms
        real_sms = redis_conn.get(sms_fmt)  # 使用redis的方法拿到答案，redis拿到的数据是byte格式的
        # 判断短信验证码
        if (not real_sms) or (sms_text != real_sms.decode('utf-8')):
            # not real_sms 这个条件是如果用户没有实行发送验证码的操作，就不可能存在答案
            # 如果在redis中没拿到sms_fmt或者用户输入的验证码不等于redis中解码出来的答案就报告
            raise forms.ValidationError("短信验证码错误")

# 登录模型
class LoginForm(forms.Form):
    '''
    # 从前端找到我们应该构建的参数
        user_account、password、remember_me
    '''
    # 拿到用户输入的参数
    user_account = forms.CharField()
    password = forms.CharField(label='密码',
                               max_length=20,
                               min_length=6,
                               error_messages={"min_length": "密码长度要大于6",
                                               "max_length": "密码长度要小于20",
                                               "required": "密码不能为空"})
    # '记住我'是一个勾选的样式，默认是不勾选
    remember_me = forms.BooleanField(required=False)

    # 继承重写init方法，为了把前端的参数和request一起传进来使用
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        '''为什么这里用get就报错？'''
        super().__init__(*args, **kwargs)

    # 单字段的校验用户名
    def clean_user_account(self):
        # 拿到用户输入的账号信息
        user_info = self.cleaned_data.get('user_account')
        # 判断账号是否为空
        if not user_info: # 如果账号为空就报告
            raise forms.ValidationError('用户不能为空！')
        # 判断账号的格式不符合下面的条件的（这里条件是取反的，如果下面两个条件有一个不满足，那就会执行不满足的）
        if not re.match(r'^1[3-9]\d{9}$', user_info) and (len(user_info)<5 or len(user_info)>20):
            raise forms.ValidationError('输入的账号格式不正确！')
        # 不满足上面两个条件的情况下，就返回账号
        return user_info

    # 联合校验用户名和密码和记住我
    def clean(self):
        # 继承重写
        cleaned_data = super().clean()
        # 拿到用户前端输入的内容
        user_info = cleaned_data.get('user_account')
        passwd = cleaned_data.get('password')   # 从前端拿到的密码是没有加密的
        hold_login = cleaned_data.get('remember_me')
        # 从数据库拿到内容
        user_queryset = Users.object.filter(Q(username=user_info) | Q(mobile=user_info))
        # 判断用户名是否为空
        if user_queryset:
            # 如果用户名是存在的，就拿到他这个实例
            user = user_queryset.first()
            # 使用check_password方法，能自动比对密码
            if user.check_password(passwd):
                # 如果密码比对正确，就判断是否有点击‘记住我’
                if not hold_login:
                    # 如果没有点击‘记住我’，就关闭浏览器就过期
                    self.request.session.set_expiry(0)
                else:
                    # 如果点击了‘记住我’，就保存5天
                    self.request.session.set_expiry(constants.USER_SESSION_EXPIRES)
                login(self.request, user) # 参数1是登录的页面，参数2是用户信息类的实例化
            # 如果密码比对错误
            else:
                raise forms.ValidationError('密码不正确，请重新输入！')
        # 如果用户名找不到
        else:
            raise forms.ValidationError('用户不存在，请重新输入！')