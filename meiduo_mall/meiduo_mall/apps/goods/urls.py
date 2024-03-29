
from django.conf.urls import url
from  . import views
urlpatterns = [
    url(r'^list/(?P<category_id>\d+)/(?P<page_num>\d+)/$',views.ListView.as_view()),
    url(r'^hot/(?P<category_id>\d+)/$',views.HotGoodsView.as_view()),
    url(r'^detail/(?P<sku_id>\d+)/$',views.DetailView.as_view(),name='detail'),
    url(r'^visit/(?P<category_id>\d+)/$',views.DetailVisitView.as_view()),
    url(r'^browse_histories/$', views.UserBrowseHistory.as_view()),
    url(r'^goods/(?P<sku_id>\d+).html/$',views.GoodsDetailView.as_view()),

]
