# 导入状态码模块
from utils.res_code import Code
# 导入返回json到前端的模块JsonResponse
from django.http import JsonResponse

# 自定义方法
# 默认状态是errno=Code.OK，报错信息是errmsg=''， 需要返回前端的内容data=None， 更多其他数据**kwargs
def to_json_data(errno=Code.OK, errmsg='', data=None, **kwargs):
    # 因为我们用json返回到前端的数据是字典格式的
    json_dict = {
        'errno': errno,
        'errmsg': errmsg,
        'data': data,
    }
    # 判断是否有其他数据且其他数据是否是字典格式且值是否为空
    if kwargs and isinstance(kwargs,dict) and kwargs.keys():
        # 字典的基本用法，更新数据内容
       json_dict.update(kwargs)
    # 返回前端
    return JsonResponse(json_dict)