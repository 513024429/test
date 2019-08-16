
from django.conf.urls import url
from  . import views
urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^register/$',views.RegisterView.as_view(),name='register'),
    url(r'^usernames/(?P<usernames>[0-9A-Za-z-_]{5,20}/count/$)',views.UsernameCountView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/',views.MobileCountView.as_view()),
    url(r'^login/$',views.LoginView.as_view()),
    url(r'^info/$',views.InfoView.as_view(),name='info'),
    url(r'^logout/$',views.LogoutView.as_view()),
    url(r'emails/$',views.EmailView.as_view()),
    url(r'^addresses/$',views.AddressesView.as_view()),
    url(r'^emails/verification/$',views.VerifyEmailView.as_view()),
    url(r'^addresses/create/$',views.CreateAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/$',views.UpdateDestroyAddressView.as_view()),
    url(r'addresses/(?P<address_id>\d+)/default/$',views.DefaultAddressView.as_view()),
    url(r'addresses/(?P<address_id>\d+)/title/$',views.UpdateTitleAddressView.as_view()),
    url(r'^password/$',views.ChangePasswordView.as_view())
]
