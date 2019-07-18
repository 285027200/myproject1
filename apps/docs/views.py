from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.encoding import escape_uri_path
import requests, logging
from .models import Doc
# Create your views here.

# 日志
logger = logging.getLogger('django')

# 函数视图，下载文档主页面
def doc_index(request):
    '''

    '''
    # 使用排除的方法获取数据库内容（与only相反）
    docs = Doc.objects.defer('author', 'create_time', 'update_time', 'is_delete')
    return render(request, 'doc/docDownload.html', locals())

# 下载功能
class DocDownload(View):
    '''
    /doc/<int:doc_id>/
    # 请求方式：get
    # 传参方式：url传
    # 返回给用户的是一个文件对象，用FileResponse
    # 思路：用户把文章id给到我们》我们根据id从数据库拿到文件的地址》通过地址拿到对象》返回给前端
    '''
    def get(self, request, doc_id):
        # 从数据库拿file_url， 判断是被删除
        doc = Doc.objects.only('file_url').filter(is_delete=False, id=doc_id).first()
        # 如果拿到数据
        if doc:
            # 拿到文件部分地址
            file_url = doc.file_url
            # 把文件地址的前缀写在settings里面，通过拼接得到完整的url
            doc_url = settings.SITE_DOMAIN_PORT + file_url
            # 检测错误
            try:
                # 使用爬虫的requests方法获取文件具体二进制内容
                file = requests.get(doc_url, stream=True)   # 优化，使用stream在下载大文件的时候可以提升下载速度
                res = FileResponse(file)
            except Exception as e:
                logger.info('获取文档内容出现异常：{}'.format(e))
                raise Http404('文档下载出错~')
            # 拿到文件地址‘.’后的后缀，从而得知文件类型
            ex_name = doc_url.split('.')[-1]
            # 判断是否拿到文件类型
            if not ex_name:
                raise Http404('文档URL异常~')
            else:
                # 拿到就转化成小写
                ex_name = ex_name.lower()
            # 判断文件类型是否符合下列内容（固定）
            if ex_name == "pdf":
                res["Content-type"] = "application/pdf"
            elif ex_name == "zip":
                res["Content-type"] = "application/zip"
            elif ex_name == "doc":
                res["Content-type"] = "application/msword"
            elif ex_name == "xls":
                res["Content-type"] = "application/vnd.ms-excel"
            elif ex_name == "docx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ex_name == "ppt":
                res["Content-type"] = "application/vnd.ms-powerpoint"
            elif ex_name == "pptx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                raise Http404("文档格式不正确！")

            # 使用django的内置方法把需要下载的文件的文件名转码成适合浏览器的格式
            doc_filename = escape_uri_path(doc_url.split('/')[-1])
            # http1.1 中的规范
            # 设置为inline，会直接打开
            # attachment 浏览器会开始下载
            res["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(doc_filename)

            # 返回前端用户
            return res
        else:
            return Http404('文档不存在！')