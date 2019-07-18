# 1.导入模块
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as _UserManager
# Create your models here.

# 7.继承UserManager和重写类
class NewUserManager(_UserManager):
    # 默认参数email为空
    def create_superuser(self, username, password, email=None, **extra_fields):
        # 重写
        super(NewUserManager, self).create_superuser(
            username=username,
            password=password,
            email=email,
            **extra_fields
        )

# 2.继承AbstractUser类，保留AbstractUser里面重要的方法
class Users(AbstractUser):
    # 8.实例化，把原来的object替换成我们重写的
    object = NewUserManager()
    # 9.用于创建超级用户是需要输入的字段，例如账号密码那样
    REQUIRED_FIELDS = ['mobile']
    # 3.添加新的字段moblie和emaile_active
    mobile = models.CharField(max_length=11, # 限定最大字数
                              unique=True,  # 设置唯一
                              verbose_name='手机号',   # 显示名称
                              help_text='手机号',  # 提示信息
                              error_messages={
                                  'unique': '此手机号已注册~'  # unique报错显示的内容
                                })
    # 4.用于是否保留邮箱的操作
    emaile_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    # 5.嵌套类，用于指定部分内容例如数据库的表名
    class Meta:
        db_table = 'tb_users'   # 指定数据库表名，不定义的话一般是app名加类的小写
        verbose_name = '用户'    # 中文显示名
        verbose_name_plural = verbose_name  # 复数名称

    # 6.打印时对象显示的内容
    def __str__(self):
        return self.username

# 10.写完代码和配置号settings之后要在manage命令行中执行数据迁移：makemigrations和migrate

    def get_groups_name(self):
        group_name_list = [i.name for i in self.groups.all()]
        return '|'.join(group_name_list)