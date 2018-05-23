# coding=utf-8
import random

from flask import current_app, jsonify, make_response,request

from ihome import redis_store, constants
from ihome.models import User
from ihome.utils.captcha.captcha import captcha
from ihome.utils.response_code import RET
from . import api
from ihome.tasks.sms import tasks


# url: /api/v1_0/image_codes/<image_code_id>
#
# methods: get
#
# 传入参数：image_code_id
#
# 返回值： 正常：图片  异常 json

@api.route("/image_codes/<image_code_id>")
def get_image_code(image_code_id):
    """提供图片验证码"""
    # 业务处理
    # 生成验证码图片 名字 验证码真实值 图片二进制内容
    name, text, image_data = captcha.generate_captcha()
    try:
        # 保存验证码的真实值和编号
        # redis_store.set("image_code_%s"%image_code_id,text)
        # 保存验证码的有效期
        # redis_store.expires("image_code_%s"%image_code_id,constants.IMAGE_CODE_REDIS_EXPIRES)

        # 保存验证码真实值和编号，有效期 setex()
        redis_store.setex("image_code_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        # 出现异常则在日志中记录异常
        current_app.logger.error(e)
        resp = {
            "errno": RET.DBERR,
            "errmsg": "保存验证码失败"
            # "errmsg":"Failed to save the verification code"
        }
        return jsonify(resp)
    # 返回验证码图片
    # 返回的Content-Type 为 image/jpg
    resp = make_response(image_data)
    resp.headers["Content-Type"] = "image/jpg"
    return resp


# # GET /api/v1_0/sms_codes/<mobile>?image_code_id=xxx&image_code=xxxx
# # 用户填写的图片验证码
# # 图片验证码的编号
# # 用户的手机号
# @api.route("/sms_codes/<re(r'1[34578]\d{9}'):mobile>")
# def send_sms_code(mobile):
#     """发送短信验证码"""
#     # 获取参数
#     # 用户填写的图片验证码
#     image_code = request.args.get("image_code")
#     # 图片验证码的编号
#     image_code_id = request.args.get("image_code_id")
#     # 校验参数
#     if not all([image_code,image_code_id]):
#         resp = {
#             "errno": RET.PARAMERR,
#             "errmsg": "数据不完整"
#             # "errmsg":"Failed to save the verification code"
#         }
#         return jsonify(resp)
#     # 业务处理
#     # 取出真实的图片验证码
#     try:
#         real_image_code = redis_store.get("image_code_%s"%image_code_id)
#     except Exception as e:
#         # 记录到日志中
#         current_app.logger.error(e)
#         resp = {
#             "errno":RET.DBERR,
#             "errmsg":"获取图片验证码失败"
#         }
#         return jsonify(resp)
#     # 判断验证码的有效期
#     if real_image_code is None:
#         # redis中没数据
#         resp = {
#             "errno": RET.NODATA,
#             "errmsg": "有效期已经过期"
#         }
#         return jsonify(resp)
#     # 删除redis中的图片验证码，防止用户多次尝试同一个验证码
#     try:
#         redis_store.delete("image_code_%s"%image_code_id)
#     except Exception as e:
#         current_app.logger.error(e)
#     # 判断用户填写的验证码与真实的验证码是否相等
#     if real_image_code.lower() != image_code.lower():
#         # 用户填写错误
#         resp = {
#             "errno": RET.DATAERR,
#             "errmsg": "验证码填写错误"
#         }
#         return jsonify(resp)
#     # 判断用户手机号是否注册
#     try:
#         user = User.query.filter_by(mobile=mobile).first()
#     except Exception as e:
#         current_app.logger.error(e)
#         resp = {
#             "errno": RET.DATAEXIST,
#             "errmsg": "手机号已经注册"
#         }
#         return jsonify(resp)
#     # 创建短信验证码
#     sms_code = "%06d"% random.randint(0,999999)
#     # 保存短信验证码
#     try:
#         redis_store.setex("sms_code_%s"%mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
#     except Exception as e:
#         current_app.logger.error(e)
#         resp = {
#             "errno": RET.DBERR,
#             "errmsg": "保存短信码异常"
#         }
#         return jsonify(resp)
#     # 发送短信验证码
#     try:
#         ccp = CCP()
#         result = ccp.send_template_sms(mobile,[sms_code,str(constants.SMS_CODE_REDIS_EXPIRES/60)],1)
#     except Exception as e:
#         current_app.logger.error(e)
#         resp = {
#             "errno": RET.THIRDERR,
#             "errmsg": "发送短信出现异常"
#         }
#         return jsonify(resp)
#     if result == 0:
#         # 发送成功
#         resp = {
#             "errno": RET.OK,
#             "errmsg": "发送成功"
#         }
#         return jsonify(resp)
#     else:
#         # 发送失败
#         resp = {
#             "errno": RET.THIRDERR,
#             "errmsg": "发送失败"
#         }
#         return jsonify(resp)
#


# GET /api/v1_0/sms_codes/<mobile>?image_code_id=xxx&image_code=xxxx
# 用户填写的图片验证码
# 图片验证码的编号
# 用户的手机号
@api.route("/sms_codes/<re(r'1[34578]\d{9}'):mobile>")
def send_sms_code(mobile):
    """发送短信验证码"""
    # 获取参数
    # 用户填写的图片验证码
    image_code = request.args.get("image_code")
    # 图片验证码的编号
    image_code_id = request.args.get("image_code_id")
    # 校验参数
    if not all([image_code,image_code_id]):
        resp = {
            "errno": RET.PARAMERR,
            "errmsg": "数据不完整"
            # "errmsg":"Failed to save the verification code"
        }
        return jsonify(resp)
    # 业务处理
    # 取出真实的图片验证码
    try:
        real_image_code = redis_store.get("image_code_%s"%image_code_id)
    except Exception as e:
        # 记录到日志中
        current_app.logger.error(e)
        resp = {
            "errno":RET.DBERR,
            "errmsg":"获取图片验证码失败"
        }
        return jsonify(resp)
    # 判断验证码的有效期
    if real_image_code is None:
        # redis中没数据
        resp = {
            "errno": RET.NODATA,
            "errmsg": "有效期已经过期"
        }
        return jsonify(resp)
    # 删除redis中的图片验证码，防止用户多次尝试同一个验证码
    try:
        redis_store.delete("image_code_%s"%image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 判断用户填写的验证码与真实的验证码是否相等
    if real_image_code.lower() != image_code.lower():
        # 用户填写错误
        resp = {
            "errno": RET.DATAERR,
            "errmsg": "验证码填写错误"
        }
        return jsonify(resp)
    # 判断用户手机号是否注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        resp = {
            "errno": RET.DATAEXIST,
            "errmsg": "手机号已经注册"
        }
        return jsonify(resp)
    # 创建短信验证码
    sms_code = "%06d"% random.randint(0,999999)
    # 保存短信验证码
    try:
        redis_store.setex("sms_code_%s"%mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
    except Exception as e:
        current_app.logger.error(e)
        resp = {
            "errno": RET.DBERR,
            "errmsg": "保存短信码异常"
        }
        return jsonify(resp)
    # 发送短信验证码
    # 使用celery发送验证码短信
    result = tasks.send_template_sms.delay(mobile,[sms_code,str(constants.SMS_CODE_REDIS_EXPIRES/60)],1)
    # 返回异步对象,通过对象获取最终执行结果
    print(result.id)
    # 通过get方法能不用自己去backend中拿取执行结果，get方法会帮助我们返回执行结果
    # get()默认是阻塞的，会等到worker执行完成有了结果的时候才会返回
    # get()通过timeout超时时间，可以在超过超时时间后立即返回
    ret = result.get()
    print(ret)
    return jsonify(errno=RET.OK, errmsg="OK")


