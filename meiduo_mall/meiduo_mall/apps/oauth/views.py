import re

from django.conf import settings
from django.contrib.auth.views import login
from django.http import JsonResponse, HttpResponse, HttpResponseServerError,HttpResponseForbidden
from django.shortcuts import render, redirect
from QQLoginTool.QQtool import OAuthQQ
# Create your views here.
from django.views.generic.base import View, logger
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from oauth.models import OAuthQQUser
from users.models import User
from .utils import generate_openid_signature, check_openid_signature


class QQAuthURLView(View):
    def get(self,request):
        next=request.GET.get('next') or '/'
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI, state=next)
        login_url = oauth.get_qq_url()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})
class QQAuthUserView(View):
    # http: // www.meiduo.site: 8000 / oauth_callback /?code = AE263F12675FA79185B54870D79730A7 & state =
    def get(self,request):
        code=request.GET.get('code')
        next=request.GET.get('state') or '/'
        if not code:
            return HttpResponse(request,'登录失败')
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI, state=next)
        try:
            # 使用code向QQ服务器请求access_token
            access_token = oauth.get_access_token(code)
            # 使用access_token向QQ服务器请求openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return HttpResponseServerError('OAuth2.0认证失败')
        try:
            user=OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            openid=generate_openid_signature(openid)
            context = {'openid': openid}
            return render(request, 'oauth_callback.html', context)
        else:
            login(request,user.user)
            response=redirect(next)
            response.set_cookie('username',user.user,max_age=3600 * 24 * 15)
            return response
    def post(self,request):
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        openid = request.POST.get('openid')
        if not all([mobile,pwd,sms_code_client,openid]):
            return HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}',mobile):
            return HttpResponseForbidden('电话号码错误')
        redis_conn=get_redis_connection('verify_code')
        ver_code=redis_conn.get('sms_%s' % mobile)
        # if ver_code is None:
        #     return JsonResponse({'code': RETCODE.SMSCODERR, 'errmsg': '短信验证码已过期'})
        # if ver_code.decode()!=sms_code_client:
        #     return JsonResponse({'code': RETCODE.SMSCODERR, 'errmsg': '短信验证码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', pwd):
            return HttpResponseForbidden('请输入8-20位的密码')
        openid=check_openid_signature(openid)
        if not openid:
            return HttpResponseForbidden('绑定失败')
        try:
            user=User.objects.get(mobile=mobile)
            if not user.check_password(pwd):
                return JsonResponse({'code': RETCODE.PWDERR, 'errmsg': '密码错误'})
        except User.DoesNotExist:
            user=User.objects.create_user(username=mobile,password=pwd,mobile=mobile)
        OAuthQQUser.objects.create(user=user, openid=openid)
        login(request, user)
        response = redirect(request.GET.get('state') or '/')
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
        return response