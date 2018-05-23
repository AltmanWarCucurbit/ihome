# coding=utf-8
from flask import Blueprint,make_response,current_app
from flask_wtf.csrf import generate_csrf

# 创建静态页面的蓝图
html = Blueprint("html", __name__)


# 提供静态的html文件
# 127.0.0.1:5000/
# 127.0.0.1:5000/index.html
# 127.0.0.1:5000/register.html
# 127.0.0.1:5000/favicon.ico  # 浏览器自动访问这个路径，获取网站的logo标志

# 注册蓝图路由
@html.route("/<re(r'.*'):file_name>")
def get_html_file(file_name):
    """提供html文件"""
    # 根据用户访问的路径的文件名file_name,提供相应的html文件
    if not file_name:
        # 如果没有file_name则默认为首页index
        file_name = "index.html"

    if file_name != "favicon.ico":
        # 如果不是网站logo则如下 拼接
        file_name = "html/" + file_name

    # 使用wtf生成csrf_token字符串
    csrf_token = generate_csrf()
    # 为用户设置cookie
    resp = make_response(current_app.send_static_file(file_name))
    resp.set_cookie("csrf_token", csrf_token)
    return resp
