# 导入模块
import json, logging
from urllib.parse import urlencode
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render
from django.views import View
from news import models
from docs.models import Doc
from users.models import Users
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from course.models import Course, CourseCategory, Teacher
from django.db.models import Count
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from utils import paginator_script
from . import constants
from datetime import datetime
from utils.fastdfs.fdfs import FDFS_Client
from myproject1 import settings
from django.http import JsonResponse, Http404
from . import forms

# 记录
logger = logging.getLogger('django')

# 管理页面的主首页
class IndexView(LoginRequiredMixin, View):
    '''
    /admin/
    '''
    # login_url = 'users:login'
    redirect_field_name = 'next'
    def get(self, request):
        return render(request, 'admin/index/index.html', locals())

# 标签管理页面（含添加操作）
class TagManageView(PermissionRequiredMixin, View):
    '''
    //
    # 返回前端：tag_name,news_num
    '''
    permission_required = ('news.add_tag', 'news.view_tag')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(TagManageView, self).handle_no_permission()

    def get(self,request):
        # 从数据库中查询tag的信息，关联上news表，先把tag中有的id和name提出来，然后用annotate拿到news的数量Count并赋值给num_news，且判断是否被删除了，和按照num_news由多到少排序(如果有相同的就按更新时间排序)
        # annotate方法，能够把两个关联的表的共同项作为条件（可以用dbug模式看下sql源码）
        tags = models.Tag.objects.select_related('news').values('id', 'name').annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news', 'update_time')
        return render(request, 'admin/news/tag_manage.html', locals())

    # 添加操作
    def post(self,request):
        # 获取前端修改的标签名
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        # 判断前端拿到的参数在数据库是否存在
        if tag_name:  # 如果拿到前端的参数
            tag_name = tag_name.strip()  # 去除多余的空格
            # get_or_create方法，返回的是一个元祖
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            # 拆包,id和name
            tag_instance, tag_boolean = tag_tuple
            if tag_boolean:
                news_tag_dict = {
                    'id': tag_instance.id,
                    'name': tag_instance.name
                }
                return to_json_data(errmsg='标签创建成功！', data=news_tag_dict)
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名已存在！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不能为空！')

# 标签编辑和删除
class TagEditView(PermissionRequiredMixin, View):
    '''
    admin/tag/<int:tag_id>/
    '''
    permission_required = ('news.delete_tag', 'news.change_tag')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    # 删除操作
    def delete(self, request, tag_id):
        # 从数据库拿到tag的id
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            # 逻辑删除
            tag.is_delete = True
            tag.save(update_fields=['is_delete'])  # 优化，只修改is_delete字段
            return to_json_data(errmsg='标签删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不存在！')

    # 编辑操作
    def put(self, request, tag_id):
        '''
        # 通过ajax获取参数
        '''
        # 获取前端修改的标签名
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')

        # 获取数据库中的tag
        tag = models.Tag.objects.only('name').filter(id=tag_id).first()
        if tag:
            # 把前端拿到的标签名进行格式化（把多余的空格去除）
            tag_name = tag_name.strip()
            # 判断前端新的标签名是否与数据库里已有的相同
            # 如果前端的新标签名与数据库里的没有相同的，就继续
            if not models.Tag.objects.only('id').filter(name=tag_name).exists():
                # 如果前端拿到的标签名和原本的标签名一样
                if tag.name == tag_name:
                    return to_json_data(errno=Code.PARAMERR, errmsg='标签未变化！')
                tag.name = tag_name
                tag.save(update_fields= ['name', 'update_time'])
                return to_json_data(errmsg='标签更新成功！')
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名已存在！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签不存在！')

# 热门文章管理页面
class HotNewsManageView(PermissionRequiredMixin, View):
    '''
        # 要获取到文章标题，文章类别，优先级，文章id
    '''
    permission_required = ('news.view_hotnews')
    raise_exception = True
    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news__tag').only('news__title', 'news__tag__name', 'priority', 'news_id').filter(is_delete=False).order_by('priority', '-news__clicks')[0:constants.SHOW_HOTNEWS_COUNT]
        return render(request, 'admin/news/news_hot.html', locals())

# 热门文章修改和删除
class HotNewsEditView(PermissionRequiredMixin, View):
    '''

    '''
    permission_required = ('news.delete_hotnews', 'news.change_hotnews')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    def delete(self, request, hotnews_id):
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if hotnews:
            hotnews.is_delete = True
            hotnews.save(update_fields= ['is_delete', 'update_time'])
            return to_json_data(errmsg='热门文章删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='删除失败！')

    def put(self, request, hotnews_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data.get('priority'))
            PRI_CHOICES = [i for i,_ in models.HotNews.PRI_CHOICES]
            if priority not in PRI_CHOICES:
                return to_json_data(errno=Code.PARAMERR, errmsg='文章优先级设置错误！')
        except Exception as e:
            logger.info('热门文章优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='文章优先级设置错误！')

        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if not hotnews:
            return to_json_data(errno=Code.PARAMERR, errmsg='热门新闻不存在！')
        if hotnews.priority == priority:
            return to_json_data(errno=Code.PARAMERR, errmsg='热门新闻优先级为改变！')
        hotnews.priority = priority
        hotnews.save(update_fields=['priority', 'update_time'])
        return to_json_data(errmsg='热门新闻优先级更新成功！')

# 热门文章添加功能
class HotNewsAddView(View):
    '''
    /admin/hotnews/add
    '''
    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news = Count('news')).filter(is_delete=False).order_by('-num_news', 'update_time')
        priority_dict = dict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_hot_add.html', locals())

    # 保存
    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            news_id = dict_data.get('news_id')
        except Exception as e:
            logger.info('热门文章错误：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误！')
        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在！')
        try:
            priority = int(dict_data.get('priority'))
            PRI_CHOICES = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in PRI_CHOICES:
                return to_json_data(errno=Code.PARAMERR, errmsg='文章优先级设置错误！')
        except Exception as e:
            logger.info('文章优先级设置错误{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='文章优先级设置错误！')
        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hotnews, is_created = hotnews_tuple
        hotnews.priority = priority
        hotnews.save(update_fields=['priority', 'update_time'])
        return to_json_data(errmsg='热门新闻创建成功！')
# 热门文章添加功能中的分支功能
class NewsByTagIdView(PermissionRequiredMixin, View):
    '''
    /admin/tags/<int:tag_id>/
    '''
    permission_required = ('news.view_news')
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    def get(self, request, tag_id):
        news = models.News.objects.filter(is_delete=False, tag_id=tag_id).values('id', 'title')
        news_list = [i for i in news]
        return to_json_data(data={
            'news': news_list
        })

# 文章管理页面的查询功能
class NewsManageView(PermissionRequiredMixin, View):
    '''
    # 请求方式: get
    # 携带的参数：?start_time=&end_time=&title=&author_name=&tag_id=5
    # 返回的参数：5个(title,author__username,tag__name,update_time,id)
    '''
    permission_required = ('news.view_news')
    raise_exception = True
    def get(self,request):
        # 一开始访问到的页面的时候，是直接拿到全部的数据（还没输入条件）
        # 拿到标签的id和name
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        # 拿到新闻的title和update_time,以及关联上author和tag,拿到author__username,tag__name
        newses = models.News.objects.select_related('author', 'tag').only('title', 'author__username', 'tag__name', 'update_time').filter(is_delete=False)

        # 通过时间进行过滤
        try:
            # 查询到的起始时间
            start_time = request.GET.get('start_time', '')
            # 对时间格式化
            start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''
            # 查询截止的时间
            end_time = request.GET.get('end_time', '')
            # 时间格式化
            end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''
        except Exception as e:
            logger.info("用户输入的时间有误：\n{}".format(e))
            start_time = end_time = ''
        # 多种时间查询情况下
        # 1.有起始时间，没有结束时间
        if start_time and not end_time:
            newses = newses.filter(update_time__gte=start_time) # 这里的newses是前面的查询集，这里使用了链式查询的方式
        # 2.有结束时间，没有起始时间
        if end_time and not start_time:
            newses = newses.filter(update_time__lte=end_time)
        # 3.起始和结束时间都有
        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))

        # 通过title进行过滤
        title = request.GET.get('title', '')
        if title:
            newses = newses.filter(title__icontains=title)  # icontains忽略大小写

        # 通过作者名进行过滤
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)

        # 通过标签id进行过滤
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info("标签错误：\n{}".format(e))
            tag_id = 0
        if tag_id:
            # 方法1：有标签id条件的时候会返回内容，没有的话会空
            newses = newses.filter(tag_id=tag_id)
            # 方法2：有标签id条件的时候会返回内容，没有的话会返回全部内容
            # newses = newses.filter(is_delete=False, tag_id=tag_id) or \
            #          newses.filter(is_delete=False)

        # 获取第几页内容
        try:
            # 获取前端的页码,默认是第一页
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info("当前页数错误：\n{}".format(e))
            page = 1
        paginator = Paginator(newses, constants.PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            news_info = paginator.page(paginator.num_pages)
        # 分页的算法
        paginator_data = paginator_script.get_paginator_data(paginator, news_info)

        # 返回前端
        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if end_time else ''
        context = {
            'news_info': news_info,
            'tags': tags,
            'start_time': start_time,
            "end_time": end_time,
            "title": title,
            "author_name": author_name,
            "tag_id": tag_id,
            # 把url的内容一致携带上(一般点击了下一页的话,前面输入的查询条件就会刷新)
            "other_param": urlencode({
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "author_name": author_name,
                "tag_id": tag_id,
            })
        }
        context.update(paginator_data) # 更新每页内容
        return render(request, 'admin/news/news_manage.html', context=context)

# 文章发布功能
class NewsPubView(PermissionRequiredMixin, View):
    '''
    /admin/news/pub/
    '''
    permission_required = ('news.view_news', 'news.add_news')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(NewsPubView, self).handle_no_permission()
    # 首先渲染出页面
    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())
    # 然后获取前端数据
    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json格式的数据转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        # 使用forms表单继承重写模型来验证和输入内容
        form = forms.NewsPubForm(data=dict_data)
        # 如果验证通过了
        if form.is_valid():
            # 把通过验证的内容进行缓存，看下我们是否需要再修改
            news_instance = form.save(commit=False) # 缓存
            # 这里也可以说是加多了一个验证，只有登录了才能发布
            news_instance.author = request.user # 我们写的forms表单验证中没有拿author字段，这里我们单独加入
            news_instance.save()
            # 返回前端
            return to_json_data(errmsg='文章发布成功！')
        # 如果没通过验证
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 文章管理页面的编辑和删除功能
class NewsEditView(PermissionRequiredMixin, View):
    '''
    /admin/news/<int:news_id>/
    '''
    permission_required = ('news.delete_news', 'news.change_news', 'news.view_news')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(NewsEditView, self).handle_no_permission()
    # 删除功能
    def delete(self, request, news_id):
        news = models.News.objects.only('id').filter(id=news_id).first()
        if news:
            news.is_delete =True
            news.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='文章删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的文章不存在！')

    # 点击编辑后进入的页面
    def get(self, request, news_id):
        news = models.News.objects.filter(id=news_id).first()
        if news:
            tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
            return render(request, 'admin/news/news_pub.html', locals())
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要编辑的文章不存在！')

    # 编辑功能
    def put(self, request, news_id):
        # 首先验证一下是否存在，防爬虫
        news = models.News.objects.filter(id=news_id).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要编辑的文章不存在！！')
        # 获取到前端输入后新的数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json格式的数据转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        # 使用forms表单继承重写模型来验证和输入内容
        form = forms.DocsPubForm(data=dict_data)
        # 如果验证通过了
        if form.is_valid():
            # 就更新清晰过后的数据
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.content = form.cleaned_data.get('content')
            news.image_url = form.cleaned_data.get('image_url')
            news.tag = form.cleaned_data.get('tag')
            # 且保存
            news.save()
            # 返回前端
            return to_json_data(errmsg='文章更新成功！')
        # 如果没通过验证
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 上传图片到服务器
class NewsUploadImage(PermissionRequiredMixin, View):
    '''

    '''
    permission_required = ('news.add_news', 'news.change_news')
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    def post(self, request):
        # 获取到前端上传的图片地址
        image_file = request.FILES.get('image_file')
        # 判断是否有内容, 如果没
        if not image_file:
            return to_json_data(errno=Code.PARAMERR, errmsg='从前端获取图片失败！')
        # 判断图片是否符合下面的几个种类，如果不符合
        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return to_json_data(errno=Code.PARAMERR, errmsg='不能上传非图片文件')
        # 要获取后缀名，有些文件是没有的，那我们就给他一个后缀
        try:
            # 拿到文件的后缀名
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'
        # 使用FDFS_Client自带的upload_by_buffer方法读取到用户的图片对象，上传到服务器中
        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.info('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传异常')
# 通过前面的upload_res = FDFS_Client。。。。。可以得到返回来的upload_res是下面的格式
# {'Group name': 'group1', 'Remote file_id': 'group1/M00/00/00/CgACD1zWZtSAARmbAAfh_rrm7jw681.png', 'Status': 'Upload successed.', 'Local file name': 'media/2018.png', 'Uploaded size': '504.00KB', 'Storage IP': '10.0.2.15'}
        # 判断是否能拿到upload_res里面返回的成功信息，如果没
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到服务器失败！')
                return to_json_data(Code.UNKOWNERR, errmsg='图片上传到服务器失败了')
            # 如果有
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功！')

# 富文本编辑器中的图片上传
class MarkDownUploadImage(View):
    """"""
    def post(self, request):
        image_file = request.FILES.get('editormd-image-file')
        # image_file = request.FILES.get('image-file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return JsonResponse({'success': 0, 'message': '从前端获取图片失败'})

        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return JsonResponse({'success': 0, 'message': '不能上传非图片文件'})

        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return JsonResponse({'success': 0, 'message': '图片上传异常'})
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return JsonResponse({'success': 0, 'message': '图片上传到服务器失败'})
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return JsonResponse({'success': 1, 'message': '图片上传成功', 'url': image_url})

# 文档管理功能
class DocsManageView(PermissionRequiredMixin, View):
    '''
    /admin/docs
    '''
    permission_required = ('doc.view_doc')
    raise_exception = True
    # 首先渲染出主要的页面
    def get(self, request):
        docs = Doc.objects.only('title', 'update_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', locals())

# 文档管理的删除和编辑功能
class DocsEditView(PermissionRequiredMixin, View):
    '''
    /admin/docs/<int:doc_id>/
    '''
    permission_required = ('doc.view_doc', 'doc.delete_doc', 'doc.change_doc')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(DocsEditView, self).handle_no_permission()
    def get(self, request, doc_id):
        doc = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg='需要编辑的文档不存在！')
        else:
            return render(request, 'admin/doc/docs_pub.html', locals())
    def delete(self, request, doc_id):
        doc = Doc.objects.filter(id=doc_id).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg='需要删除的文档不存在！')
        else:
            doc.is_delete = True
            doc.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='文档删除成功！')

    def put(self, request, doc_id):
        doc = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的文档不存在！')
        # 获取到前端输入后新的数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json格式的数据转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(doc, attr, value)
            doc.save()
            return to_json_data(errmsg='文档更新成功！')
        # 如果没通过验证
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 上传文件到服务器（和图片上传差不多，主要是要求的格式不同）
class DocsUploadFile(PermissionRequiredMixin, View):
    """
    /admin/docs/files/
    """
    permission_required = ('doc.add_doc', 'doc.change_doc')
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    def post(self,request):
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败!')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取文件失败')
        if text_file.content_type not in ('application/octet-stream', 'application/pdf',
                                          'application/zip', 'text/plain', 'application/x-rar'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件')

        try:
            text_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('文件拓展名异常：{}'.format(e))
            text_ext_name = 'pdf'

        try:
            upload_res = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name=text_ext_name)
        except Exception as e:
            logger.error('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('文件上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='文件上传到服务器失败')
            else:
                text_name = upload_res.get('Remote file_id')
                text_url = settings.FASTDFS_SERVER_DOMAIN + text_name
                return to_json_data(data={'text_file': text_url}, errmsg='文件上传成功')

# 文档的发布功能
class DocsPubView(PermissionRequiredMixin, View):
    '''
    /admin/docs/pub/
    '''
    permission_required = ('doc.view_doc', 'doc.add_doc')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(DocsPubView, self).handle_no_permission()
    def get(self, request):
            return render(request, 'admin/doc/docs_pub.html', locals())
    def post(self, request):
        # 获取到前端输入后新的数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json格式的数据转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        # 使用forms表单继承重写模型来验证和输入内容
        form = forms.DocsPubForm(data=dict_data)
        # 如果验证通过了
        if form.is_valid():
            doc_instance = form.save(commit=False)
            doc_instance.author = request.user
            doc_instance.save()
            # 返回前端
            return to_json_data(errmsg='文档更新成功！')
        # 如果没通过验证
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 课程管理（在线视频）
class CoursesManageView(PermissionRequiredMixin, View):
    """
    /admin/courses/
    """
    permission_required = ('course.view_course')
    raise_exception = True
    def get(self,request):
        courses = Course.objects.select_related('category','teacher').only('title','category__name','teacher__name').filter(is_delete=False)
        return render(request,'admin/course/courses_manage.html',locals())

# 课程编辑和删除（在线视频）
class CoursesEditView(PermissionRequiredMixin, View):
    '''
    /admin/coueses/<int:course_id>/
    '''
    permission_required = ('course.view_course', 'course.delete_course', 'course.change_course')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(CoursesEditView, self).handle_no_permission()
    def get(self, request, course_id):
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if course:
            teachers = Teacher.objects.only('name').filter(is_delete=False)
            categories = CourseCategory.objects.only('name').filter(is_delete=False)
            return render(request, 'admin/course/courses_pub.html', locals())
    def delete(self, request, course_id):
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if course:
            course.is_delete = True
            course.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='课程删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的课程不存在！')
    def put(self, request, course_id):
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if not course:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的课程不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = forms.CoursesPubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(course, attr, value)
            course.save()
            return to_json_data(errmsg='课程更新成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 课程发布功能（在线视频）
class CoursesPubView(PermissionRequiredMixin, View):
    """
    /admin/courses/pub/
    """
    permission_required = ('course.view_course', 'course.add_course')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(CoursesPubView, self).handle_no_permission()
    def get(self,request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request,'admin/course/courses_pub.html',locals())

    def post(self,request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.CoursesPubForm(data=dict_data)
        if form.is_valid():
            courses_instance = form.save()
            return to_json_data(errmsg='课程发布成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

# 组管理功能
class GroupsManageView(PermissionRequiredMixin, View):
    '''
    /admin/groups/
    '''
    permission_required = ('news.view_course')
    raise_exception = True
    def get(self, request):
        groups = Group.objects.values('id', 'name').annotate(num_users=Count('user')).order_by('-num_users', 'id')
        return render(request, 'admin/user/groups_manage.html', locals())

# 组管理的编辑和删除功能
class GroupsEditView(PermissionRequiredMixin, View):
    '''
    /admin/group/<int:group_id>/
    '''
    permission_required = ('auth.view_group', 'auth.delete_group', 'auth.change_group')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(GroupsEditView, self).handle_no_permission()
    def get(self, request, group_id):
        '''

        '''
        group = Group.objects.filter(id=group_id).first()
        if group:
            permissions = Permission.objects.only('id').all()
            return render(request, 'admin/user/groups_add.html', locals())
        else:
            raise Http404('需要更新的组不存在！')
    def delete(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if group:
            group.permissions.clear()   # 清空权限 不写也行，下面的delete会级联删除
            group.delete()
            return to_json_data(errmsg='用户组删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的用户组不存在！')

    def put(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if not group:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户组不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空！')
        if group_name != group.name and Group.objects.filter(name=group_name).exists():
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在！')
        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空！')
        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常！')
        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        # 判断是否是all的子集
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='不存在权限参数！')
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            group.permissions.add(p)    # 多对多的表添加操作
        group.name = group_name
        group.save()
        return to_json_data(errmsg='组更新成功！')

# 组管理的创建功能
class GroupsAddView(PermissionRequiredMixin, View):
    '''
    /admin/groups/add/
    '''
    permission_required = ('auth.view_group', 'auth.add_group')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(GroupsAddView, self).handle_no_permission()
    def get(self, request):
        permissions = Permission.objects.only('id').all()
        return render(request, 'admin/user/groups_add.html', locals())
    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空！')
        one_group,is_created = Group.objects.get_or_create(name=group_name)    # 返回一个元组,把它解包
        if not is_created:
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在！')
        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空！')
        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常！')
        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        # 判断是否是all的子集
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='不存在权限参数！')
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            one_group.permissions.add(p)  # 多对多的表添加操作
        one_group.save()
        return to_json_data(errmsg='组更新成功！')

# 用户管理功能
class UsersManageView(PermissionRequiredMixin, View):
    '''
    /admin/users/
    '''
    permission_required = ('users.view_users')
    raise_exception = True
    def get(self, request):
        users = Users.objects.only('username', 'is_staff', 'is_superuser').filter(is_active=True)   # is_active表示的时候，用户是否还存在
        return render(request, 'admin/user/users_manage.html', locals())

# 用户管理的编辑和删除
class UsersEditView(PermissionRequiredMixin, View):
    '''
    /admin/users/<int:user_id>/
    '''
    permission_required = ('user.view_users', 'user.change_users', 'user.delete_users')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(UsersEditView, self).handle_no_permission()
    def get(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            groups = Group.objects.only('name').all()
            return render(request, 'admin/user/users_edit.html', locals())
        else:
            return Http404('需要更新的用户不存在！')
    def delete(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            user_instance.groups.clear()
            user_instance.user_permissions.clear()
            user_instance.is_active = False # 逻辑删除，因为是逻辑删除，所有前面一定要手动的把权限清空了，不像物理删除有级联效果
            user_instance.save()
            return to_json_data(errmsg='用户删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的用户不存在！')
    def put(self, request, user_id):
        ''''''
        user_instance = Users.objects.filter(id=user_id).first()
        if not user_instance:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            groups = dict_data.get('groups')
            is_staff = int(dict_data.get('is_staff'))
            is_superuser = int(dict_data.get('is_superuser'))
            is_active = int(dict_data.get('is_active'))
            params = (is_staff, is_superuser, is_active)
            # 判断列表中是否全部为真
            if not all([p in (0, 1) for p in params]):   # 会返回一个列表[True or False]
                return to_json_data(errno=Code.PARAMERR, errmsg='参数错误！')
        except Exception as e:
            logger.info('从前端获取参数出现异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误！')
        try:
            groups_set = set(int(i) for i in groups)
        except Exception as e:
            logger.info('传的用户组参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组参数错误！')
        all_groups_set = set(i.id for i in Group.objects.only('id'))
        if not groups_set.issubset(all_groups_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组有不存在的参数！')
        gs = Group.objects.filter(id__in=groups_set)
        user_instance.groups.clear()
        user_instance.groups.set(gs)
        user_instance.is_staff = bool(is_staff)
        user_instance.is_superuser = bool(is_superuser)
        user_instance.is_active = bool(is_active)
        user_instance.save()
        return to_json_data(errmsg='用户信息更新成功！')

# 轮播图管理功能
class BannerManageView(PermissionRequiredMixin, View):
    '''
    /admin/banners/
    '''
    permission_required = ('news:view_banner')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    def get(self, request):
        banners = models.Banner.objects.only('priority', 'image_url').filter(is_delete=False).order_by('priority', 'id')[0:constants.SHOW_BANNER_COUNT]
        priority_dict = dict(models.Banner.PRI_CHOICES)
        return render(request, 'admin/news/news_banner.html', locals())

# 轮播图编辑和删除
class BannerEditView(PermissionRequiredMixin, View):
    '''
    /admin/banners/<int:banner_id>/
    '''
    permission_required = ('news.delete_banner', 'news.change_banner')
    raise_exception = True

    def delete(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if banner:
            banner.is_delete =True
            banner.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='轮播图删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的轮播图不存在！')

    def put(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的轮播图不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            PRI_CHOICES = [i for i,_ in models.Banner.PRI_CHOICES]
            if priority not in PRI_CHOICES:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图先级设置错误！')
        except Exception as e:
            logger.info('轮播图优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')

        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url不能为空！')
        if banner.priority == priority and banner.image_url == image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图参数未改变！')
        banner.image_url = image_url
        banner.priority = priority
        banner.save(update_fields = ['priority', 'image_url', 'update_time'])
        return to_json_data(errmsg='轮播图修改成功！')

# 轮播图的添加功能
class BannerAddView(PermissionRequiredMixin, View):
    '''
    /admin/banners/add/
    '''
    permission_required = ('news.view_banner', 'news.add_banner')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(BannerAddView, self).handle_no_permission()
    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news = Count('news')).filter(is_delete=False).order_by('-num_news', 'update_time')
        priority_dict = dict(models.Banner.PRI_CHOICES)
        return render(request, 'admin/news/news_banner_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            PRI_CHOICES = [i for i,_ in models.Banner.PRI_CHOICES]
            if priority not in PRI_CHOICES:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图先级设置错误！')
        except Exception as e:
            logger.info('轮播图优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('前端传过来的文章id参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误！')
        if not models.News.objects.filter(id=news_id, is_delete=False).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在！')
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url不能为空！')
        banners_tuple = models.Banner.objects.get_or_create(news_id=news_id)
        banner, is_created =banners_tuple
        banner.image_url = image_url
        banner.priority = priority
        banner.save(update_fields = ['priority', 'image_url', 'update_time'])
        return to_json_data(errmsg='轮播图创建成功！')