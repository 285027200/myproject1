# 导入模块
# 导入form表单的基本
from django import forms
# 导入django内置的用于字段使用正则来校验的方法
from django.core.validators import RegexValidator
# 导入users这个app里的模型里的Users类
from users.models import Users
# 导入redis数据库，获取链接
from django_redis import get_redis_connection

# 创建手机号码的正则校验器
mobile_validator = RegexValidator(r"^1[345789]\d{9}$", '手机号码格式不正确！')

# 检验验证码
class CheckImgCodeForm(forms.Form):
    '''
    用于检验图形验证码
    '''
    # 从auth.js文件中看到前端返回给我们用于验证的数据有三个，我们先对他们验证
    # 1.手机号
    mobile = forms.CharField(max_length=11, # 最大长度
                             min_length=11, # 最短长度
                             validators=[mobile_validator,],    # validators使用正则
                             error_messages={   # 错误信息
                                 'min_length': '手机号码长度有误',
                                 "max_length": "手机号长度有误",
                                 "required": "手机号不能为空"
                             })
    # 2.用户输入的答案
    text = forms.CharField(max_length=4,    # 最大长度
                           min_length=4,    # 最短长度
                           error_messages={ # 错误信息
                               "min_length": "图片验证码长度有误",
                               "max_length": "图片验证码长度有误",
                               "required": "图片验证码不能为空"
                           })
    # 3.uuid
    image_code_id = forms.UUIDField(error_messages={"required": "图片UUID不能为空"})

    # 重写clean方法（对多个字段一起校验，如果是clean_字段名，就是对单个字段进行校验）
    def clean(self):
        # 继承父类
        clean_data = super().clean()
        # 拿到用户输入的手机号、答案和uuid
        mobile_num = clean_data.get('mobile')
        image_text = clean_data.get('text')
        image_uuid = clean_data.get('image_code_id')

        # 拿到数据库里的手机号码的值，判断手机号是否被注册了
        if Users.object.filter(mobile=mobile_num):
            raise forms.ValidationError('手机号码已经被注册了，请重新输入！')

        # 链接上redis数据库
        con_redis = get_redis_connection(alias='verify_codes')  # 这里使用的数据库要跟之前图片验证那里的数据库一致
        # 构建好用户输入的图形验证码的key的格式
        img_key = 'img_{}'.format(image_uuid)
        # 从redis数据库中获取到图片验证码的值
        real_image_code_origin = con_redis.get(img_key) # 从redis取出来的值是字节bytes类型的
        # 判断是否有图片验证码并解码
        if real_image_code_origin:
            real_image_code = real_image_code_origin.decode('utf8')
        else:
            real_image_code = None
        '''
        三元运算符（上面if语句的）
        real_image_code = real_image_code_origin.decode('utf8') if real_image_code_origin else None
        '''
        # 删除图形验证码
        con_redis.delete(img_key)
        # 判断验证码是否符合条件
        if (not real_image_code) or (image_text != real_image_code):
            raise forms.ValidationError('图形验证失败！')

        # 60秒的检查
        sms_flg_fmt = 'sms_flag_{}'.format(mobile_num)  # 拿到用户输入的号码，构建键
        sms_flg = con_redis.get(sms_flg_fmt)    # 尝试从redis中拿取到前面构建的键
        if sms_flg: # 判断是否成功拿取键
            # 如果成功拿到了，就代表60秒内已经发送过一次了，自动存到了redis中
            # 这里的60秒在views中写了代码
            raise forms.ValidationError('获取短信验证码过于频繁~') # 存在了就报告前端