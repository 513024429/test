
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),oauth_callback /
    url(r'^qq/authorization/$',views.QQAuthURLView.as_view()),
    url(r'oauth_callback/$',views.QQAuthUserView.as_view()),
    url(r'^weibo/authorization/$',views.WeiboView.as_view()),
    url(r'^weibo/$',views.WeiBoAuthUserView.as_view()),

]
