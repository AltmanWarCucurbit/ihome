# coding=utf-8
from . import api
from ihome.models import User
from ihome import constants,db
from flask import request, jsonify, current_app,g,session
from ihome.utils.response_code import RET
from ihome.utils.image_storage import storage
from ihome.utils.commons import login_required


@api.route("/users/avatar", methods=["POST"])
@login_required
def set_user_avatar():
    """设置用户头像"""
    # 获取参数,从g对象中取,头像图片,用户
    user_id = g.user_id
    # 获取用户头像图片
    image_file = request.files.get("avatar")
    # 校验参数
    # 判断用户是否上传头像
    if image_file is None:
        # 没有上传头像
        return jsonify(errno=RET.PARAMERR,errmsg="用户未上传头像")
    # 业务处理
    # 保存用户头像数据
    image_data = image_file.read()
    try:
        file_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="上传头像异常")
    # 将用户的文件信息保存到数据库中
    try:
        User.query.filter_by(id=user_id).update({"avatar_url":file_name})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollbaack()
        return jsonify(errno=RET.DBERR,errmsg="保存头像信息失败")
    # 拼接访问路径
    avatar_url = constants.QINIU_URL_DOMAIN + file_name
    # 返回数据
    return jsonify(errno=RET.OK, errmsg="上传头像成功", data={"avatar_url": avatar_url})


@api.route("/user/name", methods=["PUT"])
@login_required
def change_user_name():
    """修改用户名"""
    # 获取用户id
    user_id = g.user_id
    # 获取用户想要设置的用户名
    req_dict = request.get_json()
    if not req_dict:
        return jsonify(errno=RET.PARAMERR,errmsg="数据不存在")
    # 获取用户要设置的名字
    name = req_dict.get("name")
    # 看用户是否设置了用户名字
    if not name:
        return jsonify(errno=RET.PARAMERR,errmsg="名字不能为空")
    # 保存用户的用户名到数据库
    try:
        User.query.filter_by(id=user_id).update({"name":name})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 失败则回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户名失败")
    # 修改session中name的值
    session["user_name"] = name
    # 返回数据保存成功
    return jsonify(errno=RET.OK,errmsg="保存用户名成功",data={"name":name})


@api.route("/user",methods=["GET"])
@login_required
def get_user_profile():
    """获取个人信息"""
    # 获取用户id
    user_id = g.user_id
    # 获取用户的信息
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.DBERR,errmsg="获取用户失败")
    # 判断用户是否存在
    if user is None:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")
    # 返回数据,获取个人信息
    return jsonify(errno=RET.OK, errmsg="获取成功", data=user.to_dict())


@api.route("/user/auth", methods=["GET"])
@login_required
def get_user_auth():
    """获取实名认证信息"""
    # 获取用户id
    user_id = g.user_id
    # 获取用户的信息
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取用户失败")
    # 判断用户是否存在
    if user is None:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")
    # 返回数据,获取实名信息
    return jsonify(errno=RET.OK, errmsg="获取成功", data=user.auth_to_dict())


@api.route("/user/auth", methods=["POST"])
@login_required
def set_user_auth():
    """保存实名认证信息"""
    # 获取用户id
    user_id = g.user_id
    # 获取前端传入的数据
    req_dict = request.get_json()
    # 判断是否有数据
    if not req_dict:
        return jsonify(errno=RET.PARAMERR,errmsg="数据不存在")
    # 获取参数,真实姓名,身份证号
    real_name = req_dict.get("real_name")
    id_card = req_dict.get("id_card")
    # 校验参数
    if not all([real_name,id_card]):
        return jsonify(errno=RET.PARAMERR,errmsg="数据不完整")
    # 保存到数据库
    try:
        User.query.filter_by(id=user_id,real_name=None,id_card=None).update({"real_name":real_name,"id_card":id_card})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="保存数据失败")
    # 返回数据,实名认证成功
    return jsonify(errno=RET.OK,errmsg="实名认证成功")
