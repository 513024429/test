
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^register/$',views.RegisterView.as_view(),name='register'),
    url(r'^usernames/(?P<usernames>[0-9A-Za-z-_]{5,20}/count/$)',views.UsernameCountView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/',views.MobileCountView.as_view()),
]
