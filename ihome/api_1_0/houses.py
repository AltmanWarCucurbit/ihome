# coding=utf-8
from . import api
from ihome.utils.response_code import RET
from ihome import constants
from flask import current_app,jsonify,request,g,session
import json
from ihome.models import Area,House,Facility,HouseImage,Order,User
from ihome import redis_store,db
from ihome.utils.commons import login_required
from ihome.utils.image_storage import storage
from datetime import datetime


@api.route("/areas")
def get_area_info():
    """获取城区信息"""
    # 先从redis中看是否有缓存
    try:
        areas_json = redis_store.get("area_info")
    except Exception as e:
        current_app.logger.error(e)
        areas_json = None
    # 如果缓存中没有数据则从数据库获取
    if areas_json is None:
        # 数据库中获取城区信息
        try:
            areas_list = Area.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(RET.DBERR,errmsg="查询信息失败")
        # 防止数据库查取的信息被其他人看见在models中定义方法
        # 遍历列表,处理每一个对象,转换对象的属性名
        areas = []
        for area in areas_list:
            areas.append(area.to_dict())
            # print(areas)
        # 将数据转换为json
        areas_json = json.dumps(areas)
        # 将数据在redis中保存一份
        try:
            redis_store.setex("area_info",constants.AREA_INFO_REDIS_EXPIRES,areas_json)
        except Exception as e:
            current_app.logger.error(e)
    else:
        # 表示redis中有缓存,则使用缓存数据
        current_app.logger.info("hit redis cache area info")
    # 返回数据
    # return jsonify(errno=RET.OK,errmsg="查询城区信息成功",data={"areas":areas})
    # 从redis中去取的json数据或者从数据库中查询并转为的是json数据
    # areas_json = '[{"aid":xx, "aname":xxx}, {},{}]'
    return '{"errno": 0, "errmsg": "查询城区信息成功", "data":{"areas": %s}}' % areas_json, 200,\
           {"Content-Type": "application/json"}


@api.route("/houses/info",methods=["POST"])
@login_required
def save_house_info():
    """保存房屋基本信息
    前端发送过来的json数据
    {
        "title": "",
        "price": "",
        "area_id": "1",
        "address": "",
        "room_count": "",
        "acreage": "",
        "unit": "",
        "capacity": "",
        "beds": "",
        "deposit": "",
        "min_days": "",
        "max_days": "",
        "facility": ["7", "8"]
    }
    """
    # 获取用户id
    user_id = g.user_id
    # 获取数据
    house_data = request.get_json()
    # 判断是否有数据
    if house_data is None:
        return jsonify(errno=RET.PARAMERR,errmsg="没有数据")
    # 获取参数
    title = house_data.get("title")  # 房屋名称标题
    price = house_data.get("price")  # 房屋单价
    area_id = house_data.get("area_id")  # 房屋所属城区的编号
    address = house_data.get("address")  # 房屋地址
    room_count = house_data.get("room_count")  # 房屋包含的房间数目
    acreage = house_data.get("acreage")  # 房屋面积
    unit = house_data.get("unit")  # 房屋布局（几室几厅)
    capacity = house_data.get("capacity")  # 房屋容纳人数
    beds = house_data.get("beds")  # 房屋卧床数目
    deposit = house_data.get("deposit")  # 押金
    min_days = house_data.get("min_days")  # 最小入住天数
    max_days = house_data.get("max_days")  # 最大入住天数

    # 校验数据
    if not all([title,price,area_id,address,room_count,acreage,unit,capacity,beds,deposit,min_days,max_days]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不完整")
    # 判断单价和押金的格式是否正确
    try:
        price = int(float(price)*100)
        deposit = int(float(deposit)*100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="参数错误")
    # 业务处理
    # 保存数据
    house = House(
        user_id=user_id,area_id=area_id,title=title,
        price=price,address=address,room_count=room_count,
        acreage=acreage,unit=unit,capacity=capacity,
        beds=beds,deposit=deposit,min_days=min_days,
        max_days=max_days
    )
    # 处理房屋设施
    # 获取所有房屋的设施
    facility_id_list = house_data.get('facility')
    if facility_id_list:
        # 过滤用户传送的不合理的设施id　获取用户勾选的设施
        try:
            facility_list = Facility.query.filter(Facility.id.in_(facility_id_list)).all()
        except  Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="查询房屋设施失败")
        # 为房屋添加设施
        if facility_list:
            house.facilities = facility_list

    # 保存数据到数据库
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="保存数据失败失败")
    # 返回数据,保存房屋基本信息成功
    return jsonify(errno=RET.OK,errmsg="保存房屋基本信息成功",data={"house_id": house.id})


@api.route("/houses/image",methods=["POST"])
@login_required
def save_house_image():
    """保存房屋图片"""
    # 获取参数,房屋id和房屋图片信息
    house_id = request.form.get("house_id")
    image_file = request.files.get("house_image")
    # 校验参数
    if not all([house_id,image_file]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不完整")
    # 判断房屋是否存在
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据查询错误")
    if house is None:
        return jsonify(errno=RET.NODATA, errmsg="房屋不存在")
    # 业务处理
    # 保存到七牛云
    image_data = image_file.read()
    try:
        file_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="保存图片失败")
    # 保存图片到数据库
    house_image = HouseImage(
        house_id=house_id,
        url=file_name
    )
    db.session.add(house_image)
    # 保存主图片到数据库
    if not house.index_image_url:
        house.index_image_url = file_name
        db.session.add(house)
        print(house.index_image_url)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 失败则回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存图片信息失败")

    image_url = constants.QINIU_URL_DOMAIN + file_name
    # 返回数据
    return jsonify(errno=RET.OK, errmsg="保存房屋图片成功", data={"image_url": image_url})


@api.route("/user/houses", methods=["GET"])
@login_required
def get_user_houses():
    """获取房东发布的房源数目"""
    # 获取用户id
    user_id = g.user_id
    # 获取用户的信息
    try:
        user = User.query.get(user_id)
        # 获取用户的房源
        houses = user.houses
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.DBERR,errmsg="用户查询错误")
    # 将查询的房源信息转为字典类型存入列表
    houses_list = []
    if houses:
        for house in houses:
            houses_list.append(house.to_basic_dict())

    # 返回数据 获取房东发布的房源信息成功
    return jsonify(errno=RET.OK, errmsg="获取信息成功", data={"houses": houses_list})


@api.route("/houses/index",methods=["GET"])
def get_house_index():
    """首页轮播图展示的房屋信息"""
    # 尝试从redis缓存中获取数据,
    try:
        ret = redis_store.get("home_page_data")
    except Exception as e:
        current_app.logger.errno(e)
        # 没有数据则设置为None
        ret = None
    if ret:
        current_app.logger.info("hit house index info redis")
        # redis中保存的数据为json,直接进行字符串拼接
        return '{"errno":0,"errmsg":"OK","data":%s}' % ret,200,{"Content-Type":"application/json"}
    else:
        # 在数据库中获取首页轮播图的房屋信息
        try:
            houses = House.query.order_by(House.order_count.desc()).limit(constants.HOME_PAGE_MAX_HOUSES)
            print(houses)
        except Exception as e:
            current_app.logger.errno(e)
            return jsonify(errno=RET.DBERR,errmsg="获取数据失败")
        # 判断房屋信息是否存在
        if not houses:
            return jsonify(errno=RET.NODATA,errmsg="无数据")

        # 将查询到的首页轮播图的房屋信息转为字典类型存入列表
        houses_list = []
        for house in houses:
            # 如果该房屋没有设置主图片,则跳过
            if not house.index_image_url:
                continue
            houses_list.append(house.to_basic_dict())

        # 将数据转为json数据
        json_houses = json.dumps(houses_list)
        print(json_houses)
        # 将数据存入一份到redis
        try:
            redis_store.setex("home_page_data",constants.HOME_PAGE_DATA_REDIS_EXPIRES,json_houses)

        except Exception as e:
            current_app.logger.errno(e)
        # 返回数据 获取首页轮播图展示的房屋信息成功
        return '{"errno":0,"errmsg":"OK","data":%s}' % json_houses, 200, {"Content-Type": "application/json"}


@api.route("/houses/<int:house_id>", methods=["GET"])
def get_house_detail(house_id):
    """获取房屋详情"""
    # 判断用户是否登录,登录则返回user_id,没有则返回-1
    user_id = session.get("user_id", "-1")
    # 校验参数
    if not house_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不存在")

    # 尝试从redis中取出缓存
    try:
        ret = redis_store.get("house_info_%s" % house_id)
    except Exception as e:
        current_app.logger.errno(e)
        # 无缓存则设置为None
        ret = None

    # 判断是否有缓存
    if ret:
        current_app.logger.info("hit house info redis")
        return '{"errno":0,"errmsg":"OK","data":{"user_id":%s,"house":%s}}' % (user_id, ret), 200, \
               {"Content-Type": "application/json"}

    # 从数据库中获取数据
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    # 判断houses是否有数据
    if not house:
        return jsonify(errno=RET.NODATA,errmsg="无数据")
    # 将详细数据转为字典数据
    try:
        house_data = house.to_full_dict()
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据出错误")
    # 将详情数据转为json类型
    json_house = json.dumps(house_data)
    # 将数据存入redis
    try:
        redis_store.setex("house_info_%s" % house_id, constants.HOUSE_DETAIL_REDIS_EXPIRE_SECOND, json_house)
    except Exception as e:
        current_app.logger.errno(e)

    # 返回数据,获取房屋详情成功
    return '{"errno":0,"errmsg":"OK","data":{"user_id":%s,"house":%s}}' % (user_id, json_house), 200, {
        "Content-Type": "application/json"}


# /api/v1_0/houses?sd=xxxx-xx-xx&ed=xxxx-xx-xx&aid=xx&sk=new&p=1
@api.route("/houses", methods=["GET"])
def get_house_list():
    """房屋的列表页"""
    # 获取参数
    start_date_str = request.args.get("sd", "")  # 查询的起始时间
    end_date_str = request.args.get("ed", "")   # 查询的结束时间
    area_id = request.args.get("aid", "")       # 区域id
    sort_key = request.args.get("sk","ner")     # 排序打关键字,默认为new最新上新的房子
    page = request.args.get("p",1)              # 页数
    # 校验参数
    # 判断数据是否完整
    if not all([start_date_str,end_date_str,area_id,sort_key,page]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不完整")
    # 判断日期是否正确
    # 如果起始时间,结束时间存在,则转换成%Y-%m-%d类型
    try:
        start_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str,"%Y-%m-%d")
        end_date = None
        if end_date_str:
            end_date = datetime.strptime(end_date_str,"%Y-%m-%d")
        # 判断日期是否正确
        if start_date and end_date:
            # 使用断言判断起始时间小于或等于结束时间
            assert start_date <= end_date
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.PARAMERR,errmsg="日期参数错误")
    # 判断页数是否为整型
    try:
        page = int(page)
    except Exception as e:
        # 不为整型则将其设置为１
        page = 1
    # 业务处理
    # 尝试从redis中获取数据
    try:
        redis_key = "houses_%s_%s_%s_%s"%(start_date_str,end_date_str,area_id,sort_key)
        resp_json = redis_store.hget(redis_key,page)
    except Exception as e:
        current_app.logger.errno(e)
        # 获取失败则表示无缓存
        resp_json = None
    # 如果拿到数据则返回数据
    if resp_json:
        return resp_json,200,{"Content-Type":"application/json"}
    # 定义一个列表表示查询的数据
    filter_params = []
    # 处理区域信息,查询地区的房源
    if area_id:
        filter_params.append(House.area_id == area_id)
    # 处理时间,查询订单冲突,获取冲突的房屋id
    try:
        confilct_orders_li = []
        if start_date and end_date:
            confilct_orders_li = Order.query.filter(Order.begin_date <= start_date, Order.end_date >= end_date).all()
        elif start_date:
            confilct_orders_li = Order.query.filter(Order.end_date >= start_date).all()
        elif end_date:
            confilct_orders_li = Order.query.filter(Order.begin_date <= end_date).all()
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库出现异常")
    # 如果冲突的房屋id不为空,
    if confilct_orders_li:
        # 遍历获取订单中的房子id
        confilct_house_id_li = [order.house_id for order in confilct_orders_li]
        # 添加条件,查询不冲突的房屋id添加到列表中
        filter_params.append(House.id.notin_(confilct_house_id_li))
    # 进行排序,入住最多,价格从高到低,价格从低到高,默认为最新的房屋
    if sort_key == "booking":
        house_query = House.query.filter(*filter_params).order_by(House.order_count.desc())
    elif sort_key == "price-inc":
        house_query = House.query.filter(*filter_params).order_by(House.price.asc())
    elif sort_key == "price-des":
        house_query = House.query.filter(*filter_params).order_by(House.price.desc())
    else:
        house_query = House.query.filter(*filter_params).order_by(House.create_time.desc())
    # 进行分页 sqlalchemy的分页
    # 获取分页的数据  页数     每页数量   错误输出
    try:
        house_page = house_query.paginate(page,constants.HOUSE_LIST_PAGE_CAPACITY,False)
    except Exception as e:
        current_app.logger.errno(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库出现异常")
    # 获取当前页的数据结果
    house_li = house_page.items
    # 总页数
    total_page = house_page.pages
    # 遍历获取当前页的房源信息,将其基本信息转为字典类型
    # 定义一个列表储存房子的信息
    houses = []
    for house in house_li:
        houses.append(house.to_basic_dict())
    # 将结果转为json字符串
    resp = dict(errno=RET.OK,errmsg="查询成功",data={"houses":houses,"total_page":total_page,"current_page":page})
    resp_json = json.dumps(resp)
    # 将结果缓存到redis中,判断页数要小于或等于总页数
    if page <= total_page:
        # 使用redis的哈希类型保存分页数据
        redis_key = "houses_%s_%s_%s_%s"%(start_date_str,end_date_str,area_id,sort_key)
        try:
            # 使用redis中的事务pipeline
            pipeline = redis_store.pipeline()
            # 开启事务 multi()
            pipeline.multi()
            pipeline.hset(redis_key,page,resp_json)
            pipeline.expire(redis_key,constants.IMAGE_CODE_REDIS_EXPIRES)
            # 执行事务,redis中事务失败会自行回滚execute()
            pipeline.execute()
        except Exception as e:
            current_app.logger.errno(e)
    # 返回数据 获取列表数据成功
    return resp_json,200,{"Content-Type":"application/json"}
