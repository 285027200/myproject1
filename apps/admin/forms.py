# 导入模块
from django import forms
from news.models import News, Tag
from docs.models import Doc
from course.models import Course

class NewsPubForm(forms.ModelForm):
    '''

    '''
    # image_url和tag字段在news的models中是允许为空的，我们重写
    image_url = forms.URLField(label='文章图片url',
                               error_messages={'required': '文章图片url不能为空'})
    # tag还要重写先找到全部的tag的id，然后给出选择只能选其中一个
    tag = forms.ModelChoiceField(queryset=Tag.objects.only('id').filter(is_delete=False),
                                 error_messages={'required': '文章标签id不能为空', 'invalid_choice': '文章标签id不存在！'})

    # 类属于模型初始化
    class Meta:
        model = News # 与数据库模型关联
        # 把需要用到的字段进行关联
        fields = ['title', 'digest', 'content', 'image_url', 'tag'] # 或者把不需要的字段用 exclude 排除
        error_messages = {
            'title': {
                'max_length': '文章标题长度不能超过150',
                'min_length': '文章标题长度至少大于1', # 这里的最小长度原来的模板中是没有的，我们需要跳回news中的models中把对应的字段加上校验器
                'required': '文章标题不能为空',
            },
            'digest': {
                'max_length': '文章标题长度不能超过150',
                'min_length': '文章标题长度至少大于1', # 这里的最小长度原来的模板中是没有的，我们需要跳回news中的models中把对应的字段加上校验器
                'required': '文章标题不能为空',
            },
            'content': {
                'required': '文章标题不能为空',
            },
        }

class DocsPubForm(forms.ModelForm):
    """
    """
    image_url = forms.URLField(label='文档缩略图url',
                               error_messages={"required": "文档缩略图url不能为空"})

    file_url = forms.URLField(label='文档url',
                               error_messages={"required": "文档url不能为空"})

    class Meta:
        model = Doc  # 与数据库模型关联
        # 需要关联的字段
        # exclude 排除
        fields = ['title', 'desc', 'file_url', 'image_url']
        error_messages = {
            'title': {
                'max_length': "文档标题长度不能超过150",
                'min_length': "文档标题长度大于1",
                'required': '文档标题不能为空',
            },
            'desc': {
                'required': '文档描述不能为空',
            },

        }

class CoursesPubForm(forms.ModelForm):
    """create courses pub form
    """
    cover_url = forms.URLField(label='封面图url',
                               error_messages={"required": "封面图url不能为空"})

    video_url = forms.URLField(label='视频url',
                               error_messages={"required": "视频url不能为空"})

    class Meta:
        model = Course  # 与数据库模型关联
        # 需要关联的字段
        # exclude 排除
        exclude = ['is_delete', 'create_time', 'update_time']
        error_messages = {
            'title': {
                'max_length': "视频标题长度不能超过150",
                'min_length': "视频标题长度大于1",
                'required': '视频标题不能为空',
            },

        }