from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, QueryDict, StreamingHttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django import forms
from django.views.generic import ListView, DetailView

from unwise import settings
from unwise.common import *
from unwise.models import *
from coadd.models import *

from astrometry.util.fits import *
from astrometry.util.starutil_numpy import *

class TileList(ListView):
    template_name = 'coadd/tile_list.html'
    paginate_by = 20
    model = Tile

dotrack = True

class CoordSearchTileList(TileList):
    def get_queryset(self):
        req = self.request
        form = RaDecSearchForm(req.GET)

        tracking = UserRaDecSearch(product=PRODUCT_COADD,
                                   ip=req.META['REMOTE_ADDR'],
                                   ra_str=form.data.get('ra',''),
                                   dec_str=form.data.get('dec',''),
                                   radius_str=form.data.get('radius',''))

        if not form.is_valid():
            if dotrack:
                tracking.save()
            return []
        ra  = form.cleaned_data['ra']
        if ra is None:
            ra = 0.
        dec = form.cleaned_data['dec']
        if dec is None:
            dec = 0
        rad = form.cleaned_data['radius']
        if rad is None:
            rad = 0.
        rad = max(0., rad)

        tracking.ra = ra
        tracking.dec = dec
        tracking.radius = rad
        if dotrack:
            tracking.save()

        tiles = unwise_tiles_near_radec(ra, dec, rad)
        tiles = list(tiles)
        #print 'N tiles:', len(tiles)
        return tiles

    def get_context_data(self, **kwargs):
        context = super(CoordSearchTileList, self).get_context_data(**kwargs)
        req = self.request
        args = req.GET.copy()
        args.pop('page', None)
        pager = context.get('paginator')
        context['total_items'] = pager.count
        context['myurl'] = req.path + '?' + args.urlencode()
        context['ra'] = args.pop('ra', [0])[0]
        context['dec'] = args.pop('dec', [0])[0]
        context['radius'] = args.pop('radius', [0])[0]
        return context

def tileset_tgz(req):
    tilenames = []
    for key,val in req.POST.items():
        if not key.startswith('tile'):
            continue
        tilenames.append(val)
    tiles = Tile.objects.filter(coadd__in=tilenames)
    maxtiles = 50
    if tiles.count() > maxtiles:
        return HttpResponse('Too many tiles requested; max %i' % maxtiles,
                            status=413)
    
    pats = []
    prods = []
    for key,pat in [('frames',  'frames.fits'),
                    ('masks',   'mask.tgz'),
                    ('imgu',    'img-u.fits'),
                    ('stdu',    'std-u.fits.gz'),
                    ('invvaru', 'invvar-u.fits.gz'),
                    ('nu',      'n-u.fits.gz'),
                    ('imgm',    'img-m.fits'),
                    ('stdm',    'std-m.fits.gz'),
                    ('invvarm', 'invvar-m.fits.gz'),
                    ('nm',      'n-m.fits.gz'),]:
        if key in req.POST:
           pats.append(pat)
           prods.append(key)

    bands = []
    for band in [1,2,3,4]:
        if 'w%i' % band in req.POST:
            bands.append(band)

    tracking = UserDownload(ip=req.META['REMOTE_ADDR'],
                            products=' '.join(prods),
                            tiles=' '.join([t.coadd for t in tiles]),
                            w1=(1 in bands),
                            w2=(2 in bands),
                            w3=(3 in bands),
                            w4=(4 in bands))
    if dotrack:
        tracking.save()
    
    # print 'Tiles:', tiles
    # print 'Bands:', bands
    # print 'Pats:', pats
    # print 'Prods:', prods
    files = []
    for tile in tiles:
        coadd = tile.coadd
        dirnm = str(os.path.join(coadd[:3], coadd))
        for band in bands:
            for pat in pats:
                files.append(str(os.path.join(dirnm, 'unwise-%s-w%i-%s' % (coadd, band, pat))))
    # print 'Files:', files
    return tar_files(req, files, 'unwise.tgz')

def tile_tgz(req, coadd=None, bands=None):
    tile = get_object_or_404(Tile, coadd=coadd)
    if bands is None:
        bands = [1,2,3,4]
        fn = '%s.tgz' % tile.coadd
    else:
        bands = [int(c,10) for c in bands]
        fn = '%s-w%s.tgz' % (tile.coadd, ''.join(['%i'%b for b in bands]))

    tracking = UserDownload(ip=req.META['REMOTE_ADDR'],
                            products='all',
                            tiles=tile.coadd,
                            w1=(1 in bands),
                            w2=(2 in bands),
                            w3=(3 in bands),
                            w4=(4 in bands))
    if dotrack:
        tracking.save()

    files = []
    coadd = tile.coadd
    dirnm = os.path.join(coadd[:3], coadd)
    base = os.path.join(dirnm, 'unwise-%s' % coadd)
    for band in bands:
        files.append(str(base + '-w%i-*' % (band)))
    return tar_files(req, files, fn)

def coord_search(req):
    if 'coord' in req.GET:
        form = CoordSearchForm(req.GET)

        tracking = UserCoordSearch(product=PRODUCT_COADD,
                                   ip=req.META['REMOTE_ADDR'],
                                   coord_str=form.data.get('coord', ''),
                                   radius_str=form.data.get('radius', ''))

        if form.is_valid():
            # Process the data in form.cleaned_data
            ra,dec = parse_coord(form.cleaned_data['coord'])
            try:
                radius = float(form.cleaned_data['radius'])
            except:
                radius = 0.

            tracking.ra = ra
            tracking.dec = dec
            tracking.radius = radius
            print 'ra,dec,radius', ra,dec,radius
            
            if dotrack:
                tracking.save()

            return HttpResponseRedirect('tiles_near/?ra=%g&dec=%g&radius=%g' % (ra, dec, radius))

        if dotrack:
            tracking.save()

    else:
        form = CoordSearchForm()

    return render(req, 'coordsearch.html', {
        'form': form,
        'url': reverse('coadd.views.coord_search'),
    })    

def index(req):
    return render(req, 'index.html')
   


def usage(req):
    import traceback
    fn = settings.DATABASES['usage']['NAME']
    ss = []
    ss.append('DB: %s, exists? %s' % (fn, os.path.exists(fn)))
    try:
        uu = UserCoordSearch.objects.all()
        uu = uu.filter(product=PRODUCT_COADD)
        ss.append('%i UserCoordSearch objects' % uu.count())
        ss.extend([str(u) for u in uu])
    except:
        ss.append('Failed to get UserCoordSearch objects')
        ss.append(traceback.format_exc())

    for cmd in [['file', fn],
                ['file', '-L', fn],
                ['sqlite3', fn, '.tables'],
                ]:
        try:
            import subprocess
            #rtn = subprocess.check_output(cmd)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            rtn = p.communicate()[0]

            ss.extend([' '.join(cmd), rtn])
        except:
            ss.append('failed to run %s' % cmd)
            ss.append(traceback.format_exc())

    try:
        uu = UserRaDecSearch.objects.all()
        uu = uu.filter(product=PRODUCT_COADD)
        ss.append('%i UserRaDecSearch objects' % uu.count())
        ss.extend([str(u) for u in uu])
    except:
        ss.append('Failed to get UserRaDecSearch objects')
        ss.append(traceback.format_exc())

    # try:
    #     uu = UserRaDecSearch(ip=req.META['REMOTE_ADDR'],
    #                          ra_str="42", dec_str="27", radius_str="1.2")
    #     uu.ra = 42.
    #     uu.dec = 27.
    #     uu.radius = 1.2
    # 
    #     ss.append('Saving: %s' % str(uu))
    #     uu.save()
    # 
    # except:
    #     ss.append('Failed to save UserRaDecSearch object')
    #     ss.append('<pre>' + traceback.format_exc() + '</pre>')


    return HttpResponse('<br/>'.join(ss))
