# 导入django自带的models
from django.db import models
import pytz # 导入显示时间的模块
from django.core.validators import MinLengthValidator # 导入最小长度校验器

# 导入基类模板
from utils.models import ModelBase

# 标签
class Tag(ModelBase):
    """"""
    name = models.CharField(max_length=64, # 最大长度
                            verbose_name="标签名", # 名称
                            help_text="标签名") # 提示
    # 原类，固定写法
    class Meta:
        ordering = ['-update_time', '-id'] # 按更新时间排序，按id大到小排序
        db_table = "tb_tag"  # 指明数据库表名
        verbose_name = "新闻标签"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称
    # 返回名称给我们看
    def __str__(self):
        return self.name

# 文章
class News(ModelBase):
    """"""
    title = models.CharField(max_length=150, validators=[MinLengthValidator(1)], verbose_name="标题", help_text="标题")
    digest = models.CharField(max_length=200, validators=[MinLengthValidator(1)], verbose_name="摘要", help_text="摘要")
    content = models.TextField(verbose_name="内容", help_text="内容")
    clicks = models.IntegerField(default=0, verbose_name="点击量", help_text="点击量")
    image_url = models.URLField(default="", verbose_name="图片url", help_text="图片url")
    # 外键关联，建在多的那头
    tag = models.ForeignKey('Tag', on_delete=models.SET_NULL, null=True)
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_news"  # 指明数据库表名
        verbose_name = "新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return self.title

# 评论
class Comments(ModelBase):
    """"""
    content = models.TextField(verbose_name="内容", help_text="内容")
    # 外键关联
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)
    news = models.ForeignKey('News', on_delete=models.CASCADE)
    # 父评论（使用外键关联他自己本身）
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    # 序列化输出（也可以用写在views中的）
    def to_dict_data(self):
        shanhai_tz = pytz.timezone('Asia/Shanghai')
        update_time_local = shanhai_tz.normalize(self.update_time)
        comment_dict = {
            'news_id': self.news_id,
            'content_id': self.id,
            'content': self.content,
            'author': self.author.username,
            'update_time': update_time_local.strftime('%Y年%m月%d日 %H:%M'),
            # 'update_time': self.update_time.strftime('%Y年%m月%d日 %H:%M'),
            'parent': self.parent.to_dict_data() if self.parent else None
        }
        return comment_dict

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_comments"  # 指明数据库表名
        verbose_name = "评论"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<评论{}>'.format(self.id)

# 热门新闻
class HotNews(ModelBase):
    """"""
    PRI_CHOICES = [
        (1,'第一级'),
        (2,'第二级'),
        (3,'第三级'),
    ]
    news = models.OneToOneField('News', on_delete=models.CASCADE)
    priority = models.IntegerField(choices=PRI_CHOICES, default=3, verbose_name="优先级", help_text="优先级")

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_hotnews"  # 指明数据库表名
        verbose_name = "热门新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<热门新闻{}>'.format(self.id)

# 轮播图
class Banner(ModelBase):
    """"""
    PRI_CHOICES = [
        (1, '第一级'),
        (2, '第二级'),
        (3, '第三级'),
        (4, '第四级'),
        (5, '第五级'),
        (6, '第六级'),
    ]
    image_url = models.URLField(verbose_name="轮播图url", help_text="轮播图url")
    priority = models.IntegerField(choices=PRI_CHOICES, default=6, verbose_name="优先级", help_text="优先级")
    news = models.OneToOneField('News', on_delete=models.CASCADE)

    class Meta:
        ordering = ['priority', '-update_time', '-id']
        db_table = "tb_banner"  # 指明数据库表名
        verbose_name = "轮播图"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<轮播图{}>'.format(self.id)