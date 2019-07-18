# django自带的模块
# 导入日志器
import logging
import json
# 导入渲染模块
from django.shortcuts import render, HttpResponse
# 导入类视图模块
from django.views import View
# 导入分页模块
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# 导入404模块
from django.http import Http404

# app下的模块
# 导入数据库模板
from . import models
# 导入常量
from . import constants
# 导入settings
from myproject1 import settings

# 其他的模块
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from haystack.views import SearchView as _SearchView

# 调用名为django的日志器
logger = logging.getLogger('django')

# 第一次测试显示主页面
def index(request):
    return render(request, 'news/index.html')

# 新闻主页
class IndexView(View):
    ''''''
    def get(self,request):
        # 查数据库里的标签的数据
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False) # 只查到没有被逻辑删除的数据的id和name
        # 查询数据库里的热门新闻的数据(通过链接的方式查询news下的title、imgage_url、id且排除掉被逻辑删除掉了的和根据priority排序或者-news__clicks排序，最后用切片的方式只取前3)
        hot_news = models.HotNews.objects.select_related('news').only('news__title', 'news__image_url', 'news__id').filter(is_delete=False).order_by('priority', '-news__clicks')[0:constants.SHOW_HOTNEWS_COUNT]
        # # 上下文管理器
        # context = {
        #     'tags': tags
        # }
        # # 返回渲染页面和数据
        # return render(request, 'news/index.html', context=context)
        # 更好的返回方法
        return render(request, 'news/index.html', locals()) # locals能把当前的变量都传过去，不用用context

# 新闻列表
class NewsListView(View):
    '''
    /news/
    # ajax局部请求刷新
    # 传参：tag的id 和page
    # 后台返回前端：拿到7个字段（文章名、标签、简介、作者名、时间、图片、文章id）
    # 请求方式：GET
    # 传参方式：查询字符串    ?tag_id1%page=2
    '''
    def get(self, request):
        # 获取前端参数（因为是用查询字符串的方法获取参数的，所以用下面的方法）
        # 校验参数
        # 用try方法是因为就算错误了还能继续运行到下一步，友好，也方便我们处理异常
        try: # 判断用户输入的参数是否正常，假如用户输的参数是字母，那就会报错
            tag_id = int(request.GET.get('tag_id', 0)) # get获取的参数是str格式的，需要int转换
        except Exception as e: # 如果用户报错，那我们就友好的给他正确的参数
            logger.error('标签的错误：\n{}'.format(e))
            tag_id = 0
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.error('页码错误：\n{}'.format(e))
            page = 1

        # 从数据库获取数据
        '''
        # 在news中查title、digest、image_url、update_time
        # 用select_related方法去关联其他的表
        '''
        # 用select_related方法去关联tag和author表，only方法只拿需要用的内容，返回的是查询集的格式
        news_queryset = models.News.objects.select_related('tag', 'author').only('title', 'digest', 'image_url', 'update_time', 'tag__name', 'author__username') # id字段是默认会查的，不用主动写入
        # 如果传的tag_id参数存在的话就直接赋值给news，或者tag_id不存在的话就赋值第二个给news
        news = news_queryset.filter(is_delete=False, tag_id=tag_id) or news_queryset.filter(is_delete=False)

        # 分页内容（把部分需要的内容给前端，不要一次性给全部）
        paginator = Paginator(news, constants.PER_PAGE_NEWS_COUNT) # 第一个参数是拿到数据，第二个参数是每页要显示的数据条数
        try: # 判断用户传的页数如否正确
            news_info = paginator.page(page)
        except EmptyPage: # 如果用户传的页数不对
            logger.error('用户访问的页数大于总页数')
            news_info = paginator.page(paginator.num_pages) # 我们就给他一个最后一页num_pages是最后一页的意思

        # 序列化输出(因为我们返回给前端的是json格式的，所以要把格式给先安排一下)
        news_info_list = []
        for n in news_info:
            news_info_list.append({
                'id': n.id,
                'title': n.title,
                'digest': n.digest,
                'image_url': n.image_url,
                # 时间的格式化
                'update_time': n.update_time.strftime('%Y年%m月%d日 %H:%M'),
                'tag_name': n.tag.name,
                'author': n.author.username,
            })
        data = {
            'news': news_info_list,
            'total_pages': paginator.num_pages,
        }

        # 返回前端
        return to_json_data(data=data)

# 轮播图
class NewsBanner(View):
    '''
    # 用ajax来传递参数
    # 要拿到轮播图表的image_url、news_id和新闻表的title
    '''
    def get(self, request):
        # 从数据库中拿去数据（直接查询Banner中的image_url和news_id，用关联news查询news__title，且排除掉被逻辑删除掉了的和根据priority排序，最后用切片的方式只取前6）
        banners = models.Banner.objects.select_related('news').only('image_url', 'news_id', 'news__title').filter(is_delete=False).order_by('priority')[0:constants.SHOW_BANNER_COUNT]
        # 序列化输出
        banners_info_list = []
        for b in banners:
            banners_info_list.append(
                {
                    'image_url':b.image_url,
                    'news_id':b.news_id,
                    'news_title':b.news.title
                }
            )
        data = {
            'banners':banners_info_list
        }
        return to_json_data(data=data)

# 文章详情
class NewsDetailView(View):
    '''
    /news/<int:news_id>
    通过模板渲染的方式来实现
    传参：文章id
    返回：5个（标题、作者、时间、标签、内容）
    '''
    def get(self, request, news_id):
        # 从数据库拿去数据(直接查询news里的title、content、update_time通过关联拿到tag__name、author__username且排除被逻辑删除了的和要求符合id=news_id，拿到第一个数据)
        news = models.News.objects.select_related('tag', 'author').only('title', 'content', 'update_time', 'tag__name', 'author__username').filter(is_delete=False, id=news_id).first()
        # 如果从数据库中拿到了数据就返回
        if news:
            # 评论功能写在这里
            # 需要从数据库拿到content, update_time, parent.username, parent.content, parent.update_time
            comments = models.Comments.objects.select_related('author', 'parent').only('content', 'update_time', 'author__username', 'parent__content', 'parent__author__username', 'parent__update_time').filter(is_delete=False, news_id=news_id)
            # 序列化输出(写在了models中)
            comments_info_list = []
            for comm in comments:
                comments_info_list.append(comm.to_dict_data())
            return render(request, 'news/news_detail.html', locals())
        # 否则报错
        else:
            raise Http404('新闻{}不存在'.format(news_id))

# 回复评论
class NewsCommentView(View):
    '''
    /news/<int:news_id>/comments/
    '''
    def post(self,request,news_id):
        # 判断用户是否有登录
        if not request.user.is_authenticated:
            return to_json_data(errno=Code.SESSIONERR, errmsg=error_map[Code.SESSIONERR])

        # 获取数据库的参数且判断是否存在
        if not models.News.objects.only('id').filter(is_delete=False, id=news_id):
            return to_json_data(errno=Code.PARAMERR, errmsg='新闻不存在')
        # 获取前端输入的参数且判断是否存在
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 校验参数
        # 拿到前端输入的内容且判断是否为空
        content = dict_data.get('content')
        if not content:
            return to_json_data(errno=Code.PARAMERR, errmsg='评论不能为空！')

        # 拿到前端输入的父评论且判断是否存在
        '''父评论的验证-1有没有父评论2parent_id必须为数字3数据库里是否存在4父评论的新闻id是否跟当前的news_id一致'''
        parent_id = dict_data.get('parent_id')
        # 因为涉及到判断是否为数字，所以要用try语句
        try:
            if parent_id:
                parent_id = int(parent_id)
                if not models.Comments.objects.only('id').filter(is_delete=False, id=parent_id, news_id=news_id).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        except Exception as e:
            logger.info('前端传的parent_id异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='未知异常')

        # 存入参数
        new_comment = models.Comments() # 实例化一个对象
        # 把对象的属性赋值
        new_comment.content = content
        new_comment.news_id = news_id
        new_comment.author = request.user
        new_comment.parent_id = parent_id if parent_id else None # 加多一层验证，防止爬虫
        new_comment.save()

        # 返回前端，使用models.py中那个序列化
        return to_json_data(data=new_comment.to_dict_data())

# 搜索功能
class SearchView(_SearchView):
    # 定义模版文件
    template = 'news/search.html'

    # 重写响应方式，如果请求参数q为空，返回模型News的热门新闻数据，否则根据参数q搜索相关数据
    def create_response(self):
        kw = self.request.GET.get('q', '') # 获取前端的url中有木有q
        # 判断有没有拿到搜索的关键字，如果没有就展示所有的
        if not kw:
            show_all = True # 展示所有数据（只是个标志而已）
            # 从HotNews表中关联的news表中拿到news__title，news__image_url，news__id且要求是没被逻辑删除的，和按优先级排序或点击量排序
            hot_news = models.HotNews.objects.select_related('news').only('news__title', 'news__image_url', 'news__id').filter(is_delete=False).order_by('priority', '-news__clicks')
            # 分页
            paginator = Paginator(hot_news, settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE)
            try:
                page = paginator.page(int(self.request.GET.get('page', 1)))
            except PageNotAnInteger:
                # 如果参数page的数据类型不是整型，则返回第一页数据
                page = paginator.page(1)
            except EmptyPage:
                # 用户访问的页数大于实际页数，则返回最后一页的数据
                page = paginator.page(paginator.num_pages)
            return render(self.request, self.template, locals())
        # 否则的意思就是拿到了关键字，那就不展示所有的数据
        else:
            show_all = False # 展示有的数据（只是个标志而已）
            # 继承和使用正宗的SearchView类的方法，上面的是被重写了的
            qs = super(SearchView, self).create_response()
            return qs