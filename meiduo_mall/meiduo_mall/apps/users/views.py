import re

from django.db import DatabaseError

from meiduo_mall.utils.response_code import RETCODE
from .models import *
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden,JsonResponse

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
        if all([username,password,password2,mobile,allow]):
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
        try:
            user=User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        return HttpResponse('注册成功，重定向到首页')
class UsernameCountView(View):
    def get(self,request,username):
        count=User.objects.filter(username=username).count()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})
class MobileCountView(View):
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})



