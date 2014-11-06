from django.conf.urls import patterns, url

from decals import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^data/$', views.data, name='data'),
    url(r'^contact/$', views.contact, name='contact')
)
