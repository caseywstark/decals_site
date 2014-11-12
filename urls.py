from django.conf.urls import patterns, url

from decals import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^data-access/$', views.data_access, name='data-access'),
    url(r'^contact/$', views.contact, name='contact')
)
