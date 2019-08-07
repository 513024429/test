
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^register/$',views.RegisterView.as_view(),name='register')
]
