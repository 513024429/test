import re

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import logout
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseForbidden,JsonResponse
from django.contrib.auth import login, authenticate
from django.db import DatabaseError
from django_redis import get_redis_connection


from meiduo_mall.utils.response_code import RETCODE
from .models import *


# Create your views here.
from django.views.generic.base import View


class RegisterView(View):
    """用户注册"""
    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')
    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        allow = request.POST.get('allow')
        if not all([username,password,password2,mobile,allow]):
            return HttpResponseForbidden('注册失败')
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return HttpResponseForbidden('请请输入5-20个字符的用户名')
        if not re.match(r'^[0-9a-zA-Z]{8,22}$',password):
            return HttpResponseForbidden('请输入8-20位的密码')
        if password!=password2:
            return HttpResponseForbidden('两次输入的密码不一致')
        if not re.match('1[3-9]\d{9}$',mobile):
            return HttpResponseForbidden('电话号码格式不对')
        if allow != 'on':
            return HttpResponseForbidden('请勾选用户协议')
        sms_code_client = request.POST.get('sms_code')
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})
        try:
            user=User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        login(request, user)
        return redirect('/index.html/')
class UsernameCountView(View):
    def get(self,request,username):
        count=User.objects.filter(username=username).count()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})
class MobileCountView(View):
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})

class LoginView(View):
    def get(self,request):
        return render(request,'/login.html/')
    def post(self,request):
        print('aa')
        username=request.POST.get('username')
        password=request.POST.get('password')
        remembered=request.POST.get('remembered')
        user=authenticate(request,username=username,password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        if remembered!='on':
            request.session.set_expiry(0)
        next=request.GET.get('next')
        login(request,user)
        print('ok')
        response=redirect(next or '/')
        response.set_cookie('username',user.username,max_age=(None if remembered is None else settings.SESSION_COOKIE_AGE))
        return response
class LogoutView(View):
    def get(self,request):
        logout(request)
        response=redirect('/login/')
        response.delete_cookie('username')
        return response
class InfoView(LoginRequiredMixin,View):
    def get(self,request):
        return render(request,'user_center_info.html')

class QQLoginView(View):
    pass






