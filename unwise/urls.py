from django.conf.urls import patterns, include, url

from coadd.views import *
from sdssphot.views import *

tilepattern = r'[0-9]{4}[pm][0-9]{3}'

urlpatterns = patterns('coadd.views',
    url(r'^tiles/$', TileList.as_view()),
    url(r'^tiles_near/$', CoordSearchTileList.as_view()),
    url(r'^tiledata/(?P<coadd>' + tilepattern +
        ')-w(?P<bands>1?2?3?4?).tgz/?$',
        'tile_tgz', name='tile-tgz'),
    url(r'^tiledata/(?P<coadd>' + tilepattern + ').tgz/?$',
        'tile_tgz', name='tile-tgz'),
    url(r'^tilesetdata/?$', 'tileset_tgz', name='tileset-tgz'),
    url(r'^imgsearch/?$', 'coord_search', name='search'),
    url(r'^search/?$', 'coord_search', name='search'),
    # url(r'^usage/?$', 'usage'),
    url(r'^$', 'index', name='index'),
)

urlpatterns += patterns('sdssphot.views',
  url(r'^photsearch/?$', 'coord_search', name='search'),
  url(r'^phot_near/?$', 'conesearch_results'),
  url(r'^phot_fieldset/?$', 'phot_fieldset_tgz', name='phot-fieldset-tgz'),
  url(r'^phot_tileset/?$', 'phot_tileset_tgz', name='phot-tileset-tgz'),
  )

### DEBUG
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

from django.conf import settings
urlpatterns += patterns(
    '',
    #url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
    #    {'document_root': settings.MEDIA_ROOT}),
    url(r'^data/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.DATA_DIR, 'show_indexes': True}),
    url(r'^data-sdssphot/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.SDSSPHOT_DATA_DIR, 'show_indexes': True}),
    )
