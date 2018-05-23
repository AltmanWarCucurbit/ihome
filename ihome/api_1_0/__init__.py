# coding=utf-8
from flask import Blueprint

# 创建蓝图对象
api = Blueprint('api_1_0', __name__)
# 告诉项目和蓝图知道index的存在
from . import index, verify_code, passport, profile, houses, orders, pay
