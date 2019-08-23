import base64
import json
import pickle
from django.shortcuts import render
from django import http
from django.views.generic.base import View

from goods import constants
from goods.models import SKU
from django_redis import get_redis_connection
from meiduo_mall.utils.response_code import RETCODE
class CartsView(View):
    def get(self,request):
        user=request.user
        if user.is_authenticated:
            redis_conn=get_redis_connection('carts')
            id=user.id
            cartsId=redis_conn.hgetall('carts_%s' % id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)
            cart_dict={}
            for sku_id, count in cartsId.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            cart_str =request.COOKIES.get('carts')
            if cart_str :
                cart_dict=pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return render(request, 'cart.html')
        sku_ids=cart_dict.keys()
        skus=SKU.objects.filter(id__in=sku_ids)
        cart_skus=[]
        for sku in skus:
            cart_skus.append({ 'id':sku.id,
                'name':sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'selected': str(cart_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
                'default_image_url':sku.default_image.url,
                'price':str(sku.price), # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount':str(sku.price * cart_dict.get(sku.id).get('count')),})
        context = {
            'cart_skus': cart_skus,
        }
        return render(request,'cart.html',context)
    def post(self,request):
        json_dict=json.loads(request.body.decode())
        sku_id=json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected',True)
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            sku=SKU.objects.get(id=sku_id)
        except Exception:
            return http.HttpResponseForbidden('商品不存在')
        try:
            count=int(count)
        except Exception:
            return http.HttpResponseForbidden('参数错误')
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')
        user=request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
        if user.is_authenticated:
            id=user.id
            redis_conn=get_redis_connection('carts')
            pl=redis_conn.pipeline()
            pl.hincrby('carts_%s' %id,sku_id,count)
            if selected:
                pl.sadd('selected_%s' %id,sku_id)
            pl.execute()
        else:
            carts_str=request.COOKIES.get('carts')
            if carts_str:
                carts_dic=pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                carts_dic={}
            if sku_id in carts_dic:
                oldcount=carts_dic[sku_id]['count']
                count=oldcount+count
            carts_dic[sku_id]={'count':count,
                               'selected':selected}
            cookie_cart_str=base64.b64encode(pickle.dumps(carts_dic)).decode()
            # 响应结果并将购物车数据写入到cookie
            response.set_cookie('carts', cookie_cart_str, max_age=constants.CARTS_COOKIE_EXPIRES)
        return response
    def put(self,request):
        json_dict=json.loads(request.body.decode())
        sku_id=json_dict.get('sku_id')
        count=json_dict.get('count')
        selected = json_dict.get('selected', True)
        user=request.user
        if not all([sku_id,count]):
            return http.HttpResponseForbidden('参数错误')
        try:
            sku=SKU.objects.get(id=sku_id)
        except Exception:
            return http.HttpResponseForbidden('商品不存在')
        try:
            count=int(count)
        except Exception:
            return http.HttpResponseForbidden('参数错误')
        if selected:
            if not isinstance(selected,bool):
                return http.HttpResponseForbidden('参数selected有误')
        if user.is_authenticated:
            redis_conn=get_redis_connection('carts')
            pl=redis_conn.pipeline()
            pl.hset('carts_%s' % user.id,sku_id,count)
            if selected:
                pl.sadd('selected_%s' % user.id,sku_id)
            else:
                pl.srem('selected_%s' % user.id,sku_id)
            pl.execute()
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})
        else:
            cart_str=request.COOKIES.get('carts')
            if not cart_str:
                return http.HttpResponseForbidden('无效参数')
            # cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            cart_dict=pickle.loads(base64.b64decode(cart_str.encode()))
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})
            # 响应结果并将购物车数据写入到cookie
            response.set_cookie('carts', cookie_cart_str, max_age=constants.CARTS_COOKIE_EXPIRES)
            return response
    def delete(self,request):
        json_dict=json.loads(request.body.decode())
        sku_id=json_dict.get('sku_id')
        user=request.user
        if user.is_authenticated:
            redis_conn=get_redis_connection('carts')
            pl=redis_conn.pipeline()
            pl.hdel('carts_%s' % user.id,sku_id)
            pl.srem('selected_%s' % user.id,sku_id)
            pl.execute()
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': "删除购物车成功"})
        else:
            carts_cls=request.COOKIES.get('carts')
            if not carts_cls:
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': 'cookie数据没获取到'})
            cart_dict=pickle.loads(base64.b64decode(carts_cls.encode()))
            if sku_id in cart_dict:
                del cart_dict[sku_id]

            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': "删除购物车成功"})
            # 判断当前字典是为空,如果为空 将cookie删除  '' () [] {} {}
            if not cart_dict:
                # 删除cookie, 删除cookie的原理 实现就是在设置cookie把它的过期时间设置为0
                response.delete_cookie('carts')
                return response

            # 字典转字符串
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 设置cookie
            response.set_cookie('carts', cart_str)
            # 响应
            return response

class CartsSimpleView(View):
    def get(self,request):
        user=request.user
        if user.is_authenticated:
            redis_conn=get_redis_connection('carts')
            redis_dict=redis_conn.hgetall('carts_%s' % user.id)
            # redis_set=redis_conn.smembers('selected_s%' % user.id)
            cart_skus=[]
            for sku_id,count in redis_dict.items():
                sku=SKU.objects.get(id=sku_id)
                data={"id":sku.id,
                      "name":sku.name,
                      "count":int(count),
                      "default_image_url":sku.default_image.url}
                cart_skus.append(data)

        else:
            carts_str=request.COOKIES.get('carts')
            if not carts_str:
                return http.JsonResponse({'code':RETCODE.OK,'error':'OK','cart_skus':{}})
            cart_dict=pickle.loads(base64.b64decode(carts_str.encode()))
            cart_skus=[]
            for sku_id in cart_dict.keys():
                sku=SKU.objects.get(id=sku_id)
                data = {"id": sku.id,
                        "name": sku.name,
                        "count": cart_dict.get(sku_id).get('count'),
                        "default_image_url": sku.default_image.url}
                cart_skus.append(data)
        return http.JsonResponse({'code': RETCODE.OK, 'error': 'OK', 'cart_skus': cart_skus})





