# coding=utf-8
from celery import Celery

# 创建celery应用对象
app = Celery("ihome")

# 读取配置
app.config_from_object("ihome.tasks.config")

# 让celery自己找到任务
app.autodiscover_tasks(["ihome.tasks.sms"])
