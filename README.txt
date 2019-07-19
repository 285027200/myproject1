准备：
  1.搭建虚拟环境
  2.pycharm设置
  3.构思数据库
    新闻news、用户users、后台admin、视频course、 文档docs、验证verifications   
  4.使用的前端是现成的模板包括css和js，还有部分是使用的bootstrap
  

流程：
  1.安装对应的apps
  2.把对应的每个接口的页面轮廓先写出来
  3.注册和登陆模块
    -重新设计用户的注册信息，添加手机号
    -在验证app使用captcha工具得到图形验证码，使用yuntongxun工具得到手机验证码
    -使用redis缓存图形验证码和手机验证码还有session
    -post请求和ajax提交信息实现注册时的数据库比对功能
  4.主页浏览模块
    -django ORM中对数据查询的优化
    -docker容器的使用
    -elasticsearch搜索功能的应用
    -评论功能以及复评论
  5.后台管理模块
    -自定义后台管理
    -借用github的AdminLTE-2.4.10的后台设计
    -自定义权限管理
  6.部署
    -静态uwsgi
    -动态nginx
    
    
