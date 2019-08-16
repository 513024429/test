import re
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.conf import settings

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from users.models import User
from verifications import constants


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
         try:
             user=User.objects.get(Q(username=username)|Q(mobile=username))
             if user.check_password(password):
                 return user
         except Exception:
             return None
def generate_email_verify_url(user):
    """拿到用户信息进行加密并拼接好激活url"""

    serializer = Serializer(settings.SECRET_KEY, 3600 * 24)

    data = {'user_id': user.id, 'email': user.email}

    token = serializer.dumps(data).decode()

    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token

    return verify_url


def check_email_verify_url(token):
    """
    对token进行解密,然后查询到用户
    :param token: 要解密的用户数据
    :return: user or None
    """
    serializer = Serializer(settings.SECRET_KEY, 3600 * 24)
    try:
        data = serializer.loads(token)
        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id=user_id, email=email)
            return user
        except User.DoesNotExist:
            return None
    except BadData:
        return None