import json
from decimal import Decimal

from django import http
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseNotFound
from django.shortcuts import render
from django.utils import timezone
from django.views.generic.base import View, logger
from django_redis import get_redis_connection

from goods import constants
from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredView
from orders.models import OrderInfo, OrderGoods, SKUComment
from users.models import Address


class OrderSettlementView(LoginRequiredView):
    def get(self,request):
        user=request.user
        addresses=Address.objects.filter(user=user, is_deleted=False)
        addresses = addresses or None
        redis_conn=get_redis_connection('carts')
        cart_selected=redis_conn.smembers('selected_%s' % user.id)
        redis_cart=redis_conn.hgetall('carts_%s' % user.id)
        cart = {}
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(redis_cart[sku_id])
        skus=SKU.objects.filter(id__in=cart.keys())
        total_count = 0
        total_amount = Decimal(0.00)
        for sku in skus:
            sku.count=cart.get(sku.id)
            sku.amount=cart.get(sku.id)*sku.price
            total_count+=sku.count
            total_amount+=sku.amount
        freight = Decimal('10.00')
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }
        return render(request, 'place_order.html', context)
class OrderCommitView(LoginRequiredView):
    def post(self,request):
        user=request.user
        json_dict=json.loads(request.body.decode())
        address_id=json_dict.get('address_id')
        pay_method=json_dict.get('pay_method')
        if not all([address_id,pay_method]):
            return http.HttpResponseForbidden('参数不能为空')
        try:
            address=Address.objects.get(id=address_id,user=user)
        except Exception:
            return http.HttpResponseForbidden('无效地址')
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')
        order_id=timezone.now().strftime('%Y%m%d%H%M%S')+('%09d'%user.id)
        redis_conn=get_redis_connection('carts')
        selected_id=redis_conn.smembers('selected_%s'%user.id)
        carts_id=redis_conn.hgetall('carts_%s'%user.id)
        carts={}
        for sku in selected_id:
            carts[int(sku)]=int(carts_id[sku])
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )
                for sku_id, count in carts.items():
                    while True:
                        sku=SKU.objects.get(id=sku_id)
                        # 定义两个变量用来记录当前sku的原本库存和销量
                        origin_stock=sku.stock
                        origin_sales = sku.sales
                        if count>origin_stock:
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})
                        result=SKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=origin_stock-count,sales=origin_sales+count)
                        if result==0:
                            continue
                        sku=SKU.objects.get(id=sku_id)
                        sku.spu.sales+=count
                        sku.spu.save()
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=count,
                            price=sku.price,
                        )
                        order.total_amount+=sku.price*count
                        order.total_count += count
                        break
                order.total_amount += order.freight
                order.save()

            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '下单失败'})
            transaction.savepoint_commit(save_id)
        pl=redis_conn.pipeline()
        pl.hdel('carts_%s'%user.id,*selected_id)
        pl.srem('selected_%s' % user.id, *selected_id)
        pl.execute()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单成功', 'order_id': order.order_id})
class OrderSuccessView(LoginRequiredView):
    """提交订单成功"""

    def get(self, request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')
                # 校验
        try:
            OrderInfo.objects.get(order_id=order_id, pay_method=pay_method, total_amount=payment_amount)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单有误')

        context = {
            'order_id':order_id,
            'payment_amount':payment_amount,
            'pay_method':pay_method
        }
        return render(request, 'order_success.html', context)
class OrderInfoView(LoginRequiredView):
    def get(self,request,page_num):
        user=request.user
        orders=OrderInfo.objects.filter(user_id=user.id)
        for order in orders:
            orderids=OrderGoods.objects.filter(order=order)
            order.pay_method_name=order.get_pay_method_display()
            order.status_name=order.get_status_display()
            order.sku_list=[]
            for orderid in orderids:
                # order.sku_list.append(orderid.sku)
                orderid.sku.count=orderid.count
                orderid.sku.amount=orderid.sku.price*orderid.count
                order.sku_list.append(orderid.sku)
        paginator = Paginator(orders, constants.GOODS_LIST_LIMIT)
        total_page = paginator.num_pages
        if int(page_num)>total_page:
            page_num=total_page
        try:
            page_orders=paginator.page(page_num)
        except Exception:
            return HttpResponseNotFound('empty page')
        context={'page_orders':page_orders,
                 'page_num':page_num,
                 'total_page':total_page}

        return render(request,'user_center_order.html',context)
class OrderCommentView(LoginRequiredView):
    def get(self,request):
        order_id=request.GET.get('order_id')
        sku_ids=OrderGoods.objects.filter(order_id=order_id)
        skus=[]
        for sku in sku_ids:
            sku_id={'sku_id':sku.sku.id,
                    'name':sku.sku.name,
                    'price':str(sku.sku.price),
                    'default_image_url':sku.sku.default_image.url,
                    'order_id':order_id}
            skus.append(sku_id)
        context={'uncomment_goods_list':skus}
        return render(request,'goods_judge.html',context)
    def post(self,request):
        user=request.user
        json_dict=json.loads(request.body.decode())
        comment=json_dict.get('comment')
        is_anonymous=json_dict.get('is_anonymous')
        score=json_dict.get('score')
        sku_id=json_dict.get('sku_id')
        order_id=json_dict.get('order_id')
        username=user.username
        if not all([sku_id,comment,order_id]):
            return http.HttpResponseForbidden('参数不能为空')
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')
        if is_anonymous:
            is_anonymous=True
            username='null'
        with transaction.atomic():
            savepoint = transaction.savepoint()
            try:
                SKUComment.objects.create(
                    sku_id=sku_id,
                    score=score,
                    is_anonymous=is_anonymous,
                    comment=comment,
                    order_id=order_id,
                    username=username
                )
                OrderInfo.objects.filter(order_id=order_id).update(status=5)
                transaction.savepoint_commit(savepoint)
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(savepoint)
                return http.HttpResponseForbidden('评价失败')
        return http.JsonResponse({'code':RETCODE.OK})