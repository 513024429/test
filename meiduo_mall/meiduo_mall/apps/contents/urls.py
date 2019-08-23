
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^$',views.IndexView.as_view()),
    url(r'^index.html/$',views.IndexView.as_view()),

]
