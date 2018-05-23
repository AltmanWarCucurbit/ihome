# coding=utf-8
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from ihome import create_app, db

# 创建flask的app
app = create_app("develop")

# 创建管理工具对象
manage = Manager(app)
Migrate(app, db)
manage.add_command('db', MigrateCommand)


@app.route('/index')
def index():
    return "welcome to index"


if __name__ == '__main__':
    manage.run()
