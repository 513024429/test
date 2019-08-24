from django.shortcuts import render,redirect
import json
from django.core.paginator import Paginator
from django.utils import timezone
from django_redis import get_redis_connection
from django.views.generic.base import View, logger
from django import http
from django.core.urlresolvers import reverse

from meiduo_mall.utils.views import LoginRequiredView
from meiduo_mall.utils.views import get_categories
from .utils import get_breadcrumb,get_commnets
from .models import GoodsCategory,SKU,GoodsVisitCount
from . import constants
from meiduo_mall.utils.response_code import RETCODE
class ListView(View):
    #获取商品列表页
    def get(self,request,category_id,page_num):
        categories = get_categories()
        try:
            category =GoodsCategory.objects.get(id=category_id)
        except Exception:
            return http.HttpResponseForbidden('没有分类')
        breadcrumb=get_breadcrumb(category)
        sort=request.GET.get('sort')
        if sort=='price':
            sort_field='price'
        elif sort=='hot':
            sort_field='-sales'
        else:
            sort = 'default'
            sort_field = 'create_time'
        skus=SKU.objects.filter(category_id=category_id,is_launched=True).order_by(sort_field)
        # 创建分页器：每页N条记录
        paginator=Paginator(skus,constants.GOODS_LIST_LIMIT)
        total_page=paginator.num_pages
        if int(page_num)>=int(total_page):
            page_num=total_page
        page_skus=paginator.page(page_num)

        # paginator = Paginator(skus, constants.GOODS_LIST_LIMIT)
        # try:
        #     page_skus = paginator.page(page_num)
        # except EmptyPage:
        #     # 如果page_num不正确，默认给用户404
        #     return http.HttpResponseNotFound('empty page')
        context = {
            'categories': categories,
            'breadcrumb':breadcrumb,
            'category':category,
            'page_skus':page_skus,
            'sort':sort,
            'total_page':total_page,
            'page_num':page_num
            }
        return render(request, 'list.html',context)
class HotGoodsView(View):
    #获取热销商品
    def get(self,request,category_id):
        try:
            skus=SKU.objects.filter(category_id=category_id).order_by('-price')
        except Exception:
         return http.HttpResponseForbidden('参数错误')
        hotList=[]
        hotGood={
            'id':'',
            'default_image_url':'',
            'name':'',
            'price':''
        }
        for sku in skus:
            hotGood['id']=sku.id
            hotGood['default_image_url']=sku.default_image.url
            hotGood['name']=sku.name
            hotGood['price']=sku.price
            hotList.append(hotGood)
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'SUCCESS','hot_skus':hotList})
class DetailView(View):
    def get(self,request,sku_id):
        """提供商品详情页"""
        # 获取当前sku的信息
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')
        category =sku.category
        spu = sku.spu
        # 查询商品规格
        # current_sku_spec_qs
        current_sku_spec_qs=sku.specs.order_by('spec_id')
        current_sku_option_ids = []
        for current_sku_spec in current_sku_spec_qs:
            current_sku_option_ids.append(current_sku_spec.option_id)
        temp_sku_qs = spu.sku_set.all()
        spec_sku_map = {}
        for temp_sku in temp_sku_qs:
            # 查询每一个sku的规格数据
            temp_spec_qs = temp_sku.specs.order_by('spec_id')
            temp_sku_option_ids = []  # 用来包装每个sku的选项值
            for temp_spec in temp_spec_qs:
                temp_sku_option_ids.append(temp_spec.option_id)
            spec_sku_map[tuple(temp_sku_option_ids)] = temp_sku.id

        """3.组合 并找到sku_id 绑定"""
        spu_spec_qs = spu.specs.order_by('id')  # 获取当前spu中的所有规格

        for index, spec in enumerate(spu_spec_qs):  # 遍历当前所有的规格
            spec_option_qs = spec.options.all()  # 获取当前规格中的所有选项
            temp_option_ids = current_sku_option_ids[:]  # 复制一个新的当前显示商品的规格选项列表
            for option in spec_option_qs:  # 遍历当前规格下的所有选项
                temp_option_ids[index] = option.id  # [8, 12]
                option.sku_id = spec_sku_map.get(tuple(temp_option_ids))  # 给每个选项对象绑定下他sku_id属性

            spec.spec_options = spec_option_qs  # 把规格下的所有选项绑定到规格对象的spec_options属性上
        comments,count=get_commnets(sku_id)
        context = {
            'categories': get_categories(),  # 商品分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sku': sku,  # 当前要显示的sku模型对象
            'category': category,  # 当前的显示sku所属的三级类别
            'spu': spu,  # sku所属的spu
            'spec_qs': spu_spec_qs,  # 当前商品的所有规格数据
            'comments':comments,
            'peoples':count
        }
        return render(request, 'detail.html', context)
class DetailVisitView(View):
    """详情页分类商品访问量"""

    def post(self, request, category_id):
        """记录分类商品访问量"""
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('缺少必传参数')

        today_date = timezone.now()  # 获取当天的日期

        try:
            # 查询当天有没有访问过此类别商品
            counts_data = GoodsVisitCount.objects.get(date=today_date, category=category)
        except GoodsVisitCount.DoesNotExist:
              # 如果没有访问过就创建一个新记录
            counts_data = GoodsVisitCount(
                category=category
            )

        counts_data.count += 1  # 增加访问量
        counts_data.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
class UserBrowseHistory(LoginRequiredView):
    def post(self,request):
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        user_id=request.user.id
        try:
            SKU.objects.get(id=sku_id)
        except Exception:
            return http.HttpResponseForbidden('sku无效')
        redis_conn=get_redis_connection('history')
        pl=redis_conn.pipeline()
        pl.lrem('history_%s' % user_id,0,sku_id)
        pl.lpush('history_%s' % user_id, sku_id)
        # 最后截取
        pl.ltrim('history_%s' % user_id, 0, 4)
        # 执行管道
        pl.execute()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
    def get(self,request):
        user_id=request.user.id
        redis_conn=get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)
        skus=[]
        data={}
        for sku_id in sku_ids:
            quertSku=SKU.objects.get(id=sku_id)
            data['id']=quertSku.id
            data['name']=quertSku.name
            data['default_image_url'] = quertSku.default_image.url
            data['price'] = quertSku.price
            skus.append(data)
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})
class GoodsDetailView(View):
    def get(self,request,sku_id):
        url=reverse('goods:detail',args=(sku_id,))
        return redirect(url)

