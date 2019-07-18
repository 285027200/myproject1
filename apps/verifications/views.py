# 导入模块
from django.shortcuts import render # 基本的渲染模块
from django.http import HttpResponse, JsonResponse    # 同上
from django.views import View   # 继承模板类视图
from utils.captcha.captcha import captcha   # 生成图片验证码的模块
# 导入redis数据库的模块
from django_redis import get_redis_connection
# 把常量单独保存，导入使用
from verifications import constants
# 导入日志器
import logging
# 导入用户在数据库的信息模块，users里的models
from users import models
# 导入自定义的返回json的方法
from utils.json_fun import to_json_data
# 导入json模块
import json
# 导入自定义的状态码和报错信息
from utils.res_code import Code, error_map
# 导入用于验证码的form表单
from verifications.forms import CheckImgCodeForm
# 导入随机模块，和字符串模块
import random, string
# 导入云通讯模块
from utils.yuntongxun.sms import CCP

# 指定使用的django日志器
logger = logging.getLogger('django')

# 图片验证码验证
class ImageCode(View):
    '''
    image_codes
    '''
    # 前端返回内容给后端，如果与数据库有关联就用post，没有就用get
    def get(self, request, image_code_id):
        # 把调用验证码返回的两个数据赋值给text和image
        text, image = captcha.generate_captcha()
        # 链接我们的redis数据库verify_codes
        con_redis = get_redis_connection(alias='verify_codes')
        # 因为redis存数据是用键值对的形式，我们先自定义一个键
        img_key = 'img_{}'.format(image_code_id)
        # img_key是键，constants.IMAGE_CODE_REDIS_EXPIRES是有效期，text是值也是我们的答案
        con_redis.setex(img_key, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        # 在终端上打印出验证码
        logger.info('Image code: {}'.format(text))
        # 返回内容，指定格式
        return HttpResponse(content=image, content_type='image/jpg')

# 用户名查重验证
class CheckUsernameView(View):
    '''
    # 用re_path来对url先进行一次验证
    /username/(?P<username>\w{5,20})/
    '''
    # 1.请求方式
    def get(self, request, username):
        # 查询数据库里是否有符合条件的内容，有就返回数量count
        count = models.Users.object.filter(username=username).count()
        # 构造一个返回的json对象
        data = {
            'count': count,
            'username': username,
        }
        # return JsonResponse({'data': data})
        return to_json_data(data=data)

# 手机验证
class CheckMobileView(View):
    '''
    /mobiles/(?P<mobile>1[3-9]\d{9})/
    '''
    def get(self, request, mobile):
        count = models.Users.object.filter(mobile=mobile).count()
        data = {
            'count': count,
            'mobile': mobile,
        }
        # return JsonResponse({'data': data})
        return to_json_data(data=data)

# 短信验证
'''
当点击发送验证码时，要完成下面的操作
1.验证手机：不能为空，手机号的格式，手机号是否注册过
2.验证码：不能为空，uuid对比
3.uuid：格式，唯一性
'''
class SmsCodesView(View):
    '''
    /sms_codes/
    '''
    # 获取数据，涉及到隐私和数据库，使用post方法
    def post(self, request):
        # 直接获取到request里json返回的内容
        json_data = request.body    # 拿到的内容是字节的格式
        # 判断是否能获取到参数
        if not json_data:
            # 如果不能就返回错误信息
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 使用json方法把json格式的内容转成字典格式
        dict_data = json.loads(json_data.decode('utf8'))    # 因为前面获取的内容是字节格式的，所以要先解码为utf-8格式
    # 验证参数(使用form表单)
        form = CheckImgCodeForm(data=dict_data)
        # 判断是否通过前面的验证
        if form.is_valid():
            # 如果通过，随机生成短信
            # 从表单中拿到用户输入的手机号码
            mobile = form.cleaned_data.get('mobile')
            # 定义一个空的字符串
            sms_num = ''
            # 随机生成6位数的短信验证码
            for i in range(6):
                sms_num += random.choice(string.digits) # 随机拿6个数字组成验证码
            '''
            更好的方法：
            sms_num = ''.join([random.choice(string.digits) for _ in range(contants.SMS_CODE_NUMS)])
            '''
            # 保存短信验证码
            # 连接redis数据库
            con_redis = get_redis_connection(alias='verify_codes')
            # redis的管道服务，能把两个key同时存入
            pl = con_redis.pipeline()
            # 构建手机短信验证码的key
            sms_text_fmt = 'sms_{}'.format(mobile)
            # 构建验证码发送的标记的key
            sms_flg_fmt = 'sms_flag_{}'.format(mobile)
            try:
                pl.setex(sms_flg_fmt, constants.SEND_SMS_CODE_INTERVAL, constants.SMS_CODE_TEMP_ID)    # 参数为：构建的key，有效期，标记
                pl.setex(sms_text_fmt, constants.SMS_CODE_REDIS_EXPIRES, sms_num)    # 参数为：构建key，有效期，随机验证码
                pl.execute()    # 发送数据到redis
            except Exception as e:
                logger.debug('redis,执行异常了：{}'.format(e))
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
            # 发送短信验证码
            logger.info('发送短信验证码[成功~][ mobile: %s sms_code: %s]' % (mobile, sms_num))
            return to_json_data(errno=Code.OK, errmsg='短信验证码发送成功~')
            # try:
            #     result = CCP().send_template_sms(mobile,
            #                                      [sms_num,constants.SMS_CODE_REDIS_EXPIRES],
            #                                      constants.SMS_CODE_TEMP_ID)
            # except Exception as e:
            #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
            #     return to_json_data(errno=Code.SMSERROR, errmsg=error_map[Code.SMSERROR])
            # else:
            #     if result == 0:
            #         logger.info("发送验证码短信[正常][ mobile: %s sms_code: %s]" % (mobile, sms_num))
            #         return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")
            #     else:
            #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
            #         return to_json_data(errno=Code.SMSFAIL, errmsg=error_map[Code.SMSFAIL])
        # 返回前端
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)