# coding=utf-8
import re
from . import api
from ihome import redis_store,db
from ihome.models import User
from flask import request,jsonify,current_app,session
from ihome.utils.response_code import RET
from ihome import constants


# POST /api/v1_0/users
@api.route("/users",methods=["POST"])
def register():
    """用户注册"""
    # 接受参数
    # 使用request.get_json 或 json.loads(request.data)将json数据转化为字典类型
    req_dict = request.get_json()
    # 获取手机号,短信验证码,密码
    mobile = req_dict.get("mobile")
    print(type(mobile))
    sms_code = req_dict.get("sms_code")
    password = req_dict.get("password")
    # 校验参数
    if not all([mobile,sms_code,password]):
        resp = {
            "errno":RET.PARAMERR,
            "errmsg":"参数数据不完整"
        }
        return jsonify(resp)
    # 判断手机号格式是否正确
    if not re.match(r"1[34578]\d{9}", mobile):
        resp = {
            "errno": RET.DATAERR,
            "errmsg": "手机号格式不正确"
        }
        return jsonify(resp)
    # 业务处理
    # 获取真实短信的验证码
    try:
        real_sms_code = redis_store.get("sms_code_%s"% mobile)
        print(real_sms_code)
    except Exception as e:
        current_app.logger.error(e)
        resp = {
            "errno": RET.DBERR,
            "errmsg": "查询短信验证码错误"
        }
        return jsonify(resp)
    # 判断短信有效期是否过期
    if real_sms_code is None:
        resp = {
            "errno": RET.NODATA,
            "errmsg": "短信有效期已过期"
        }
        return jsonify(resp)
    # 判断用户输入的短信验证码是否正确
    if real_sms_code != sms_code:
        resp = {
            "errno": RET.DATAERR,
            "errmsg": "验证码输入错误"
        }
        return jsonify(resp)
    # 删除验证码,防止用户多次重复输入
    try:
        redis_store.delete("sms_code_%s"% mobile)
    except Exception as e:
        current_app.logger.error(e)
    # 判断手机号是否注册
    # try:
    #     user = User.query.filter_by(mobile=mobile).first()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     resp = {
    #         "errno": RET.DBERR,
    #         "errmsg": "数据库异常"
    #     }
    #     return jsonify(resp)
    #
    # if user is not None:
    #     # 表示已经注册过
    #     resp = {
    #         "errno": RET.DATAEXIST,
    #         "errmsg": "用户手机号已经注册"
    #     }
    #     return jsonify(resp)
    # 保存数据到数据库
    user = User(name=mobile, mobile=mobile)
    # 对于password属性的设置，会调用属性方法，进行加密操作
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        # 表示已经注册过
        resp = {
            "errno": RET.DATAEXIST,
            "errmsg": "用户手机号已经注册"
        }
        return jsonify(resp)
    # 记住当前登录状态
    session["user_id"] = user.id
    session["user_name"] = mobile
    session["mobile"] = mobile
    # 返回数据,注册成功
    resp = {
        "errno": RET.OK,
        "errmsg": "注册成功"
    }
    return jsonify(resp)


@api.route("/sessions", methods=["POST"])
def login():
    """登录"""
    # 获取参数,手机号,密码
    # 使用request.get_json 或 json.loads(request.data)将json数据转化为字典类型
    req_dict = request.get_json()
    # 获取手机号
    mobile = req_dict.get("mobile")
    # 获取密码
    password = req_dict.get("password")
    # 校验参数
    # 判断数据是否完整
    if not all([mobile,password]):
        return jsonify(errno=RET.PARAMERR,errmsg="数据不完整")
    # 判断手机格式是否正确
    if not re.match(r"1[34578]\d{9}",mobile):
        return jsonify(errno=RET.PARAMERR,errmsg="手机格式不正确")
    # 业务处理
    # 判断用户的错误次数，从redis获取错误次数 remote_addr取出ip地址信息
    user_ip = request.remote_addr
    try:
        access_count = redis_store.get("access_%s"%user_ip)
    except Exception as e:
        current_app.logger.error(e)
    else:
        # 如果错误记录超过最大次数，则直接返回
        if access_count is not None and int(access_count) >= constants.LOGIN_ERROR_MAX_NUM:
            return jsonify(errno=RET.REQERR, errmsg="登录太过频繁,请稍后在登录")
    # 用户的user用户名是否存在,密码是否一致
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询用户信息异常")
    # 判断用户的user用户名是否存在,密码是否正确
    if user is None or not user.check_password(password):
        # 出现错误则累加错误次数,incr
        try:
            redis_store.incr("access_%s"%user_ip)
            redis_store.expire("access_%s"%user_ip,constants.LOGIN_ERROR_FORBID_TIME)
        except Exception as e:
            current_app.logger.error(e)
        return jsonify(errno=RET.LOGINERR, errmsg="用户登录失败")
    # 登录成功,则清除用户登录错误次数
    try:
        redis_store.delete("access_%s"%user_ip)
    except Exception as e:
        current_app.logger.error(e)
    # 记住用户当前的登录状态
    session["user_name"] = user.name
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    # 返回数据 登录成功
    return jsonify(errno=RET.OK,errmsg="登录成功")


@api.route("/session", methods=["GET"])
def check_login():
    """检验登录状态"""
    # 从session中获取用户的名字
    name = session.get("user_name")
    # 如果session中用户名字存在则表示已经登录
    if name is not None:
        return jsonify(errno=RET.OK, errmsg="true", data={"name": name})
    else:
        return jsonify(errno=RET.SESSIONERR, errmsg="false")


@api.route("/session", methods=["DELETE"])
def logout():
    """退出登录"""
    # 清除session数据
    session.clear()
    return jsonify(errno=RET.OK,errmsg="OK")
