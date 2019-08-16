from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings

from verifications import constants


def generate_openid_signature(openid):
    """
    签名openid
    :param openid: 用户的openid
    :return: 加密后的openid
    """
    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.ACCESS_TOKEN_EXPIRES)
    data = {'openid': openid}
    token = serializer.dumps(data)
    return token.decode()
def check_openid_signature(openid_sign):
    """对openid进行解密, 并返回原始的openid"""
    # 1.创建加密/解密实例对象
    serializer = Serializer(settings.SECRET_KEY, 600)
    try:
        # 2.调用loads方法进行解密
        data = serializer.loads(openid_sign)
    except BadData:
        return None

    # 3.返回
    return data.get('openid')