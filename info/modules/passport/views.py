from flask import request, jsonify, current_app, make_response

from info import redis_store
from info.modules.passport import passport_blue
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET


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
        redis_store.set("image_code_%s", image_code_id, 3600)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询失败')
    resp = make_response(image)
    resp.headers["Content-Type"] = 'image/jpg'
    return resp
