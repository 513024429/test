from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views.generic.base import View
from django.core.cache import cache

from meiduo_mall.utils.response_code import RETCODE
from .models import Area

class AreasView(View):
    def get(self,request):
        area_id=request.GET.get('area_id')
        if area_id is None:
            province_list = cache.get('province_list')
            if not province_list:
                try:
                    province_model_list = Area.objects.filter(parent__isnull=True)
                    province_list=[]
                    for province_model in province_model_list:
                        province_list.append({'id': province_model.id, 'name': province_model.name})
                except Exception:
                    return HttpResponseForbidden('查询失败')
                cache.set('province_list',province_list,3600)
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:
            try:
                parent_model = Area.objects.get(id=area_id)
            except Area.DoesNotExist:
                return HttpResponseForbidden('area_id不存在')
            # 通过上级查询出下级所有行政区
            sub_data=cache.get('subs_%s' % area_id)
            if not sub_data:
                sub_qs = parent_model.subs.all()

                sub_list = []  # 用来装所有下级 行政区
                for sub_model in sub_qs:
                    sub_list.append({
                        'id': sub_model.id,
                        'name': sub_model.name
                    })

                # 定义字典变量 包装前端需要的数据
                sub_data = {
                    'id': parent_model.id,
                    'name': parent_model.name,
                    'subs': sub_list
                }

            # 缓存下级行政区数据
                cache.set('subs_%s' % area_id, sub_data, 3600)
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})


# Create your views here.
