import json
import re
from django.urls import reverse
from celery_tasks.email.tasks import send_verify_url
from django.conf import settings
from django.contrib.auth import mixins
from django.contrib.auth.views import logout
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, HttpResponseServerError, \
    HttpResponseBadRequest
from django.contrib.auth import login, authenticate
from django.db import DatabaseError
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from users.utils import generate_email_verify_url, check_email_verify_url
from .models import *
from meiduo_mall.utils.views import LoginRequiredView
from django.views.generic.base import View, logger


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
class InfoView(LoginRequiredView):
    def get(self,request):
        user=request.user
        print(user)
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html', context=context)
class EmailView(LoginRequiredView):
    def put(self,request):
        json_dict =json.loads(request.body.decode())
        email=json_dict.get('email')
        if not email:
            return HttpResponseForbidden('邮箱不能为空')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return HttpResponseForbidden('邮箱格式错误')
        user = request.user
        # 3.1 修改它的email字段
        user.email = email
        user.save()
        verify_url=generate_email_verify_url(user)
        send_verify_url.delay(email, verify_url)
        return JsonResponse({'code':RETCODE.OK,'errmsg':'添加邮箱成功'})

class VerifyEmailView(LoginRequiredView):
    def get(self,request):
        token = request.GET.get('token')

        # 校验参数：判断token是否为空和过期，提取user
        if not token:
            return HttpResponseBadRequest('缺少token')

        user = check_email_verify_url(token)
        if not user:
            return HttpResponseForbidden('无效的token')

        # 修改email_active的值为True
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseServerError('激活邮件失败')

        # 返回邮箱验证结果
        return redirect(reverse('users:info'))

class AddressesView(LoginRequiredView):
    """用户收货地址"""
    def get(self, request):
        user=request.user
        default_address_id=user.default_address_id
        addresses=Address.objects.filter(user=user,is_deleted=False)
        address_list=[]
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            address_list.append(address_dict)

        contentx={
            'default_address_id':default_address_id,
            'addresses':address_list
        }
        return render(request, 'user_center_site.html',contentx)
class CreateAddressView(LoginRequiredView):
    def post(self,request):
        user=request.user
        count=user.addresses.count()
        if count>20:
            return JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超过地址数量上限'})
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return HttpResponseForbidden('缺少必传参数')
        if not re.match(r'1[3-9]\d{9}',mobile):
            return HttpResponseForbidden('mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match('^[0-9a-z][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$'):
                return HttpResponseForbidden('参数email有误')
        try:
            address =Address.objects.create(
                    user=user,
                    title=receiver,
                    receiver=receiver,
                    province_id=province_id,
                    city_id=city_id,
                    district_id=district_id,
                    place=place,
                    mobile=mobile,
                    tel=tel,
                    email=email)
            if not user.default_address:
                user.default_address=address
                user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code':RETCODE.DBERR, 'errmsg': '新增地址失败'})
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "province_id":province_id,
            "city": address.city.name,
            "city_id":city_id,
            "district": address.district.name,
            "district_id":district_id,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address':address_dict})
class UpdateDestroyAddressView(LoginRequiredView):
    def put(self,request,address_id):
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return HttpResponseForbidden('缺少必传参数')
        if not re.match(r'1[3-9]\d{9}',mobile):
            return HttpResponseForbidden('mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match('^[0-9a-z][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$'):
                return HttpResponseForbidden('参数email有误')
        user=request.user
        try:
            Address_user=Address.objects.get(id=address_id)
            Address_user.title =receiver
            Address_user.receiver=receiver
            Address_user.province_id = province_id
            Address_user.city_id  = city_id
            Address_user.district_id  = district_id
            Address_user.place  = place
            Address_user.mobile  = mobile
            Address_user.tel  = tel
            Address_user.email = email
            Address_user.save()
        except Exception as e:
            # logger.error(e)
            # return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新地址失败'})
            logger.error(e)
            return JsonResponse({'code':RETCODE.DBERR,'errmsg':'更新地址失败'})
        address_dict ={
            "id": Address_user.id,
            "title": Address_user.title,
            "receiver": Address_user.receiver,
            "province": Address_user.province.name,
            "province_id":Address_user.province_id,
            "city": Address_user.city.name,
            "city_id":Address_user.city_id,
            "district": Address_user.district.name,
            "district_id":Address_user.district_id,
            "place": Address_user.place,
            "mobile": Address_user.mobile,
            "tel": Address_user.tel,
            "email": Address_user.email
        }
        return JsonResponse({'code':RETCODE.OK,'errmsg':'更新地址成功','address':address_dict})
    def delete(self,request,address_id):
        user=request.user
        try:
            address=Address.objects.get(user=user,id=address_id)
            address.is_deleted=True
            address.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})
        return JsonResponse({'code':RETCODE.OK,'errmsg':'删除地址成功'})
class DefaultAddressView(LoginRequiredView):
    def put(self,request,address_id):
        user=request.user
        try:
            address=Address.objects.get(id=address_id,user=user)
            user.default_address=address
            user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址失败'})
        return JsonResponse({'code':RETCODE.OK,'errmsg':'设置地址成功'})
class UpdateTitleAddressView(LoginRequiredView):
    def put(self,request,address_id):
        user=request.user
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        try:
            address=Address.objects.get(id=address_id,user=user)
            address.title=title
            address.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

            # 4.响应删除地址结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})
class ChangePasswordView(LoginRequiredView):
    def get(self,request):
        return render(request,'user_center_pass.html')
    def post(self,request):
        user=request.user
        old_password = request.POST.get('old_pwd')
        new_password = request.POST.get('new_pwd')
        new_password2 = request.POST.get('new_cpwd')
        if not all([old_password, new_password, new_password2]):
            return HttpResponseForbidden('缺少必传参数')
        if request.user.check_password(old_password) is False:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return HttpResponseForbidden('密码最少8位，最长20位')
        if new_password != new_password2:
            return HttpResponseForbidden('两次输入的密码不一致')
        try:
            user.password=new_password
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseForbidden('保存密码失败')
        logout(request)
        response = redirect(reverse('users:login'))
        response.delete_cookie('username')
        return response






