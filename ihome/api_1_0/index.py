# coding=utf-8
import logging
from . import api
from flask import current_app
from ihome import models


@api.route('/index')
def index():
    # logging.error('err')
    # current_app在视图函数中读取参数，读取logging
    current_app.logger.error('error msg')  # 错误级别
    current_app.logger.warn('warn msg')    # 警告级别
    current_app.logger.info('info msg')    # 消息提示级别
    current_app.logger.debug('debug msg')  # 调试级别
    return "welcome to index"
