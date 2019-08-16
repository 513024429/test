
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),oauth_callback /
    url(r'^areas/$',views.AreasView.as_view())
]
