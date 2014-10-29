from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden, QueryDict, StreamingHttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django import forms
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import tempfile

from unwise.common import *
from unwise.models import *
from sdssphot.models import *

from astrometry.util.fits import *
from astrometry.util.starutil_numpy import *
from astrometry.libkd.spherematch import *

from unwise import settings

dotrack = True
#dotrack = False

version_choices = [
    ('sdss-dr10d', 'SDSS DR10'),
    ('sdss-dr13',  'SDSS DR13 (requires SDSS password)'),
    ('eboss',      'eBOSS targeting (requires SDSS password)'),
    #('sequels',    'SEQUELS targeting (requires SDSS password)'),
    ]
version_default = 'sdss-dr10d'

password_versions = ['sdss-dr13', 'eboss']
#, 'sequels']

sdssurls = {
    'sdss-dr10d': 'http://data.sdss3.org/sas/dr10/boss/photoObj/301/',
    'sdss-dr13' : 'http://data.sdss3.org/sas/ebosswork/eboss/photoObj.v5b/301/',
    'eboss'     : 'http://data.sdss3.org/sas/ebosswork/eboss/photoObj.v5b/301/',
    }

datatype_choices = [
    ('flat', 'Flat FITS table'),
    ('wise', 'WISE tiles in range'),
    ('sdss', 'SDSS fields in range')
    ]
datatype_default = 'flat'

def get_phot_data_url(version, dtype):
    version = str(version)
    if version in password_versions:
        return settings.SDSSPHOT_DATA_URL + '/sdss-collab/' + version + '-' + dtype + '/'
    return settings.SDSSPHOT_DATA_URL + '/' + version + '-' + dtype + '/'

def get_phot_data_path(version, dtype):
    version = str(version)
    if version in password_versions:
        return os.path.join(settings.SDSSPHOT_DATA_DIR, 'sdss-collab', version + '-' + dtype)
    return os.path.join(settings.SDSSPHOT_DATA_DIR, version + '-' + dtype)

# mix-in
class SdssPhotForm(forms.Form):
    sdss = forms.BooleanField(required=False, initial=False)

    version = forms.ChoiceField(required=False, initial=version_default,
                                choices=version_choices)

    datatype = forms.ChoiceField(required=True, initial=datatype_default,
                                 choices=datatype_choices)

    password = forms.CharField(widget=forms.PasswordInput(),#render_value=True),
                               required=False)

    def clean(self):
        if self.cleaned_data['datatype'] == 'flat':
            if self.cleaned_data['radius'] > 1.:
                raise ValidationError('For flat FITS tables, the maximum search radius is 1 degree')
        if self.cleaned_data['datatype'] == 'sdss':
            if self.cleaned_data['radius'] > 10.:
                raise ValidationError('For SDSS fields, the maximum search radius is 10 degrees')

        version = str(self.cleaned_data['version'])
        print 'Version', version
        if version is None or len(version) == 0:
            version = version_default
        print 'Version', version
        if not version in [k for k,v in version_choices]:
            raise ValidationError('Unknown version')
        print 'known version'
        if version in password_versions:
            password = self.cleaned_data['password']
            if not password in settings.SDSS_PASSWORDS:
                raise ValidationError('Incorrect password.  Contact dstn@cmu.edu for help.')
            print 'password okay'
        else:
            print 'public version'
        self.cleaned_data['version'] = version
        return self.cleaned_data

class SdssPhotCoordSearchForm(CoordSearchForm, SdssPhotForm):
    pass

class SdssPhotRaDecSearchForm(RaDecSearchForm, SdssPhotForm):
    pass

    
tempdir = os.environ.get('TMPDIR', os.environ.get('TMP', '/tmp'))
def create_temp(**kwargs):
    f,fn = tempfile.mkstemp(dir=tempdir, **kwargs)
    os.close(f)
    os.unlink(fn)
    return fn

    
'''
SDSS fields:

Start with subset resolve-2010-05-23-cut/window_flist.fits
which has only fields containing SDSS >= 1 primary objects,

T=fits_table('window_flist.fits')
T.cut(T.rerun == '301')
T.camcol = T.camcol.astype(np.uint8)
T.field = T.field.astype(np.int16)
T.run = T.run.astype(np.int16)
T.writeto('window_flist_cut.fits', columns=['ra','dec','run','camcol','field'])

from astrometry.libkd.spherematch import *
kd = tree_build_radec(ra=T.ra, dec=T.dec)
tree_save(kd, 'window_flist_cut.kd')
I = np.arange(int(len(T))).astype(np.int32)
print 'Permute...', I.dtype, I.shape
tree_permute(kd, I)
tree_free(kd)
K = T[I]
print 'Append...'
K.writeto('window_flist_cut.kd', append=True,
    columns=['run','camcol','field','ra','dec'])
'''

class mytabledata(tabledata):
    def __getitem__(self, I):
        if isinstance(I, basestring):
            raise TypeError('Cannot index using string')
        return super(mytabledata, self).__getitem__(I)

def phot_tileset_tgz(req):

    version = req.POST.get('version', None)
    if version is None:
        version = version_default
    if version in password_versions:
        if not req.session.get('authenticated', False):
            return HttpResponseForbidden('password required')

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

    files = []
    for tile in tiles:
        coadd = tile.coadd
        files.append(str('phot-%s.fits' % tile.coadd))
    basedir = get_phot_data_path(version, 'phot')
    return tar_files(req, files, 'wisephot.tgz', basedir=basedir)

def phot_fieldset_tgz(req):

    version = req.POST.get('version', None)
    if version is None:
        version = version_default
    if version in password_versions:
        if not req.session.get('authenticated', False):
            return HttpResponseForbidden('password required')

    fields = []
    for key,val in req.POST.items():
        if not key.startswith('field'):
            continue
        terms = val.split('/')
        if len(terms) != 3:
            return HttpResponse('failed to parse field "%s"' % val)
        try:
            terms = [int(t,10) for t in terms]
        except:
            return HttpResponse('failed to parse field "%s"' % val)
        fields.append(terms)
    maxfields = 1000
    if len(fields) > maxfields:
        return HttpResponse('Too many fields requested; max %i' % maxfields,
                            status=413)

    files = []
    for run,camcol,field in fields:
        fn = ('%i/%i/photoWiseForced-%06i-%i-%04i.fits' %
              (run, camcol, run, camcol, field))
        files.append(fn)
    basedir = get_phot_data_path(version, 'pobj')
    #print 'basedir', basedir
    #print 'files', files
    return tar_files(req, files, 'wisephot.tgz', basedir=basedir)

def conesearch_results(req):
    #
    form = SdssPhotRaDecSearchForm(req.GET)
    if not form.is_valid():
        print 'Form not valid'
        return HttpResponseRedirect(reverse(coord_search))

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
    version = form.cleaned_data['version']
    # if version is None or version == '':
    #     version = version_default
    dtype = form.cleaned_data['datatype']
    if dtype is None or dtype == '':
        dtype = datatype_default

    if version in password_versions:
        # if the form validated, the password matched.
        req.session['authenticated']  = True
        req.session['version'] = version

    if dtype in ['flat', 'sdss']:
        # FIXME -- this is resolve-specific, ie version-specific.
        kdfn = settings.WINDOW_FLIST_KD
        # Find SDSS fields in range.
        kd = tree_open(kdfn)
        # enlarge search radius by SDSS field size
        srad = rad + np.hypot(14.,10.)/60./2.
        #print 'Search radius:', srad, 'deg'
        I,nil = tree_search_radec(kd, ra, dec, srad,
                              sortdists=True)
        tree_close(kd)
        #print 'Search result:', len(I), 'fields'
        if len(I):
            T = fits_table(kdfn, hdu=6, rows=I, tabledata_class=mytabledata)
        else:
            T = tabledata()

    if dtype == 'flat':
        TT = []
        #print len(T), 'SDSS fields'
        #print 'version', ver
        for run,camcol,field in zip(T.run, T.camcol, T.field):
            fn = os.path.join(get_phot_data_path(version, 'pobj'),
                              '%i'%run, '%i'%camcol,
                              'photoWiseForced-%06i-%i-%04i.fits' %
                              (run, camcol, field))
            if not os.path.exists(fn):
                #print 'Does not exist:', fn
                continue
            tt = fits_table(fn)
            if tt is None:
                continue
            #print len(tt), 'from', fn
            tt.cut(tt.objid != '                   ')
            #print len(tt), 'with objids'
            if len(tt) == 0:
                continue
            tt.cut(degrees_between(ra, dec, tt.ra, tt.dec) <= rad)
            if len(tt) == 0:
                continue
            n = len(tt)
            tt.run = np.empty(n, np.int16)
            tt.run[:] = run
            tt.camcol = np.empty(n, np.uint8)
            tt.camcol[:] = camcol
            tt.field = np.empty(n, np.int16)
            tt.field[:] = field
            TT.append(tt)
        if len(TT) == 0:
            return HttpResponseBadRequest('No objects match your query.')
        T = merge_tables(TT)
        del TT
        #print 'Total of', len(T), 'sources'
        #print 'has_wise_phot:', np.unique(T.has_wise_phot)
        tempfn = create_temp()
        ### HACK!!
        T.has_wise_phot = np.ones(len(T), bool)
        T.writeto(tempfn)
        del T
        res = StreamingHttpResponse(open(tempfn))
        os.unlink(tempfn)
        res['Content-type'] = 'application/fits'
        res['Content-Disposition'] = 'attachment; filename="sdsswise.fits"'
        return res

    if dtype == 'sdss':
        args = req.GET.copy()
        args.pop('page', None)
        T.path = np.array(['%s/%s/photoWiseForced-%06i-%i-%04i.fits' %
                           (t.run, t.camcol, t.run, t.camcol, t.field)
                           for t in T])
        keep = []
        base = get_phot_data_path(version, 'pobj')
        for i,p in enumerate(T.path):
            if os.path.exists(os.path.join(base, p)):
                keep.append(i)
        if len(keep) == 0:
            return HttpResponseBadRequest('No objects match your query. (%i listed)' % len(T))
        T.cut(np.array(keep))

        T.filename = np.array(['photoWiseForced-%06i-%i-%04i.fits' %
                           (t.run, t.camcol, t.field) for t in T])
        T.sdssurl = np.array([sdssurls[version] +
                              '%s/%s/photoObj-%06i-%i-%04i.fits' %
                              (t.run, t.camcol, t.run, t.camcol, t.field)
                              for t in T])
        T.sdssfile = np.array(['photoObj-%06i-%i-%04i.fits' %
                              (t.run, t.camcol, t.field) for t in T])

        ctxt = {
            'total_items': len(T),
            'object_list': T,
            'ra': ra,
            'dec': dec,
            'radius': rad,
            'version': version,
            'dataurl': get_phot_data_url(version, 'pobj'),
            'myurl': req.path + '?' + args.urlencode()
            }
        pagination = 20
        if len(T) > pagination*1.5:
            paginator = Paginator(T, pagination)
            page = req.GET.get('page')
            try:
                page = paginator.page(page)
            except PageNotAnInteger:
                page = paginator.page(1)
            except EmptyPage:
                # 9999 -> last page
                page = paginator.page(paginator.num_pages)
            # print 'Page:', page
            # print 'has_next', page.has_next()
            ctxt.update(
                paginator = paginator,
                is_paginated = True,
                page_obj = page,
                object_list = page,
                )
        
        return render(req, 'sdssphot/field_list.html', ctxt)

    if dtype == 'wise':
        tiles = unwise_tiles_near_radec(
            ra, dec, rad,
            tablename='sdssphot_phottile',
            extra_where="and version='%s'" % version,
            tileclass=PhotTile)
        tiles = list(tiles)
        print 'N tiles:', len(tiles)
        args = req.GET.copy()
        args.pop('page', None)

        ctxt = {
            'total_items': len(tiles),
            'object_list': tiles,
            'ra': ra,
            'dec': dec,
            'radius': rad,
            'version': version,
            'dataurl': get_phot_data_url(version, 'phot'),
            'myurl': req.path + '?' + args.urlencode()
            }

        pagination = 20
        if len(tiles) > pagination*1.5:
            paginator = Paginator(tiles, pagination)
            pagenum = req.GET.get('page')
            try:
                page = paginator.page(pagenum)
            except PageNotAnInteger:
                page = paginator.page(1)
            except EmptyPage:
                # 9999 -> last page
                page = paginator.page(paginator.num_pages)
            ctxt.update(
                paginator = paginator,
                is_paginated = True,
                page_obj = page,
                object_list = page,
                )
        return render(req, 'sdssphot/tile_list.html', ctxt)
    
def coord_search(req):
    if 'coord' in req.GET:
        form = SdssPhotCoordSearchForm(req.GET)

        tracking = UserCoordSearch(product=PRODUCT_SDSSPHOT,
                                   ip=req.META['REMOTE_ADDR'],
                                   coord_str=form.data.get('coord', None),
                                   radius_str=form.data.get('radius', None))

        if form.is_valid():
            print 'Form is valid: data', form.cleaned_data

            # Process the data in form.cleaned_data
            ra,dec = parse_coord(form.cleaned_data['coord'])
            try:
                radius = float(form.cleaned_data['radius'])
            except:
                radius = 0.

            tracking.ra = ra
            tracking.dec = dec
            tracking.radius = radius
            if dotrack:
                tracking.save()

            datatype = form.cleaned_data['datatype']
            version = form.cleaned_data['version']
            password = form.cleaned_data['password']

            url = 'phot_near/?ra=%g&dec=%g&radius=%g&datatype=%s' % (ra, dec, radius, datatype)
            if len(version):
                url += '&version=%s' % version
            if len(password):
                url += '&password=%s' % password
            if form.cleaned_data['sdss']:
                url += '&sdss'
            return HttpResponseRedirect(url)

        # form not valid

        print form
        
        if dotrack:
            tracking.save()

    else:
        form = SdssPhotCoordSearchForm()
        form.initial = dict(coord='200 10', radius=0.1)
        
    return render(req, 'sdssphot/coordsearch.html', {
        'sdsscollab': 'sdss' in req.GET,
        'form': form,
        'version_choices': version_choices,
        'datatype_choices': datatype_choices,
        'url': reverse('sdssphot.views.coord_search'),
        'dataurl': settings.SDSSPHOT_DATA_URL,
    })    

