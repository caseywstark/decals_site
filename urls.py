from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'decals.views.index', name='index'),
    url(r'^data-access/$', 'decals.views.data_access', name='data-access'),
    url(r'^contact/$', 'decals.views.contact', name='contact'),
    url(r'^maps/$', 'maps.views.index', name='maps'),
    url(r'^maps/decals/(\d*)/(\d*)/(\d*).jpg', 'maps.views.map_decals'),
    url(r'^maps/decals-model/(\d*)/(\d*)/(\d*).jpg', 'maps.views.map_decals_model'),
)
