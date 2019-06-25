import random
import re
from datetime import datetime

from flask import request, jsonify, current_app, make_response, session

from info import redis_store, constants, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.modules.passport import passport_blue
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET


@passport_blue.route('/register', methods=['POST'])
def register():
    # 获取参数
    params_dict = request.json
    mobile = params_dict.get('mobile')
    sms_code = params_dict.get('sms_code')
    password = params_dict.get('password')

    # 校验参数
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    if not re.match(r'1[3-9]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')
    try:
        real_sms_code = redis_store.get('sms_code_%s' % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')
    if not real_sms_code:
        return jsonify(errno=RET.PARAMERR, errmsg='短信验证码已过期')
    if sms_code.upper() != real_sms_code.upper():
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码不正确')

    # 业务处理
    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile
    user.last_login = datetime.now()
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库保存错误')

    # 记录登录状态
    session['user_id'] = user.id
    session['mobile'] = user.mobile
    session['nick_name'] = user.nick_name

    return jsonify(errno=RET.OK, errmsg='注册成功')


@passport_blue.route('/send_sms_codes', methods=['POST'])
def send_sms_codes():
    # 获取参数
    params_dict = request.json
    mobile = params_dict.get('mobile')
    image_code = params_dict.get('image_code')
    image_code_id = params_dict.get('image_code_id')

    # 校验参数
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数有误')
    if not re.match(r'1[3-9]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')
    try:
        real_image_code = redis_store.get('image_code_%s' % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')
    if not real_image_code:
        return jsonify(errno=RET.PARAMERR, errmsg='图片验证码已过期')
    if image_code.upper() != real_image_code.upper():
        return jsonify(errno=RET.DATAERR, errmsg='图片验证码不正确')

    # 业务逻辑
    sms_code = "%06d" % random.randint(0, 999999)
    current_app.logger.debug("短信验证码为: %s" % sms_code)
    try:
        redis_store.set("sms_code_%s" % mobile, sms_code, 3600)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询失败')

    result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES], "1")

    return jsonify(errno=RET.OK, errmsg='发送成功')


@passport_blue.route('/image_codes')
def image_codes():
    # 获取参数
    image_code_id = request.args.get('image_code_id', None)

    # 校验参数
    if not image_code_id:
        return jsonify(errno=RET.PARAMERR, errmsg='参数有误')

    # 业务处理
    name, text, image = captcha.generate_captcha()
    current_app.logger.debug("图片验证码为: %s" % text)
    try:
        redis_store.set("image_code_%s" % image_code_id, text, 3600)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询失败')
    resp = make_response(image)
    resp.headers["Content-Type"] = 'image/jpg'
    return resp
