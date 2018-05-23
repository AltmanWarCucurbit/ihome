# coding=utf-8
from functools import wraps
from flask import session,jsonify,g
from ihome.utils.response_code import RET
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    """自定义接受正则的路由转换器"""
    def __init__(self,url_map,regex):
        """regex为路由中的正则"""
        super(RegexConverter, self).__init__(url_map)
        self.regex = regex


def login_required(view_func):
    """检验用户的登录状态"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is not None:
            # 用户已登录
            # 用g对象保存user_id,视图可以直接调用
            g.user_id = user_id
            return view_func(*args, **kwargs)
        else:
            resp = {
                "errno": RET.SESSIONERR,
                "errmsg": "用户为登录"
            }
            return jsonify(resp)

    return wrapper
